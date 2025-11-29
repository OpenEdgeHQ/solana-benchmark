from solana.rpc.async_api import AsyncClient, GetTransactionResp
from typing import Dict, Any, List
from solders.transaction_status import ParsedInstruction
from spl.token.instructions import get_associated_token_address
from solders.pubkey import Pubkey
from decimal import Decimal

def _parse_balances(tx_result: GetTransactionResp, agent_pubkey: str):
    meta = tx_result.value.transaction.meta
    token_info = {}
    total_balances = {
        "pre_balance": meta.pre_balances[0],
        "post_balance": meta.post_balances[0],
        "fee": meta.fee,
        "category": "balance",
    }
    if meta.pre_token_balances:
        pre_token_balance = []
        for pre_token_bal in meta.pre_token_balances:
            ata = get_associated_token_address(Pubkey.from_string(agent_pubkey), pre_token_bal.mint)
            token_info[str(pre_token_bal.mint)] = pre_token_bal.ui_token_amount.decimals
            token_info[str(ata)] = pre_token_bal.ui_token_amount.decimals
            pre_token_balance.append({
                "owner": str(pre_token_bal.owner),
                "mint": str(pre_token_bal.mint),
                "ui_amount": pre_token_bal.ui_token_amount.ui_amount_string
            })
        total_balances["pre_token_balance"] = pre_token_balance
    if meta.post_token_balances:
        post_token_balance = []
        for post_token_bal in meta.post_token_balances:
            ata = get_associated_token_address(Pubkey.from_string(agent_pubkey), post_token_bal.mint)
            token_info[str(post_token_bal.mint)] = post_token_bal.ui_token_amount.decimals
            token_info[str(ata)] = post_token_bal.ui_token_amount.decimals
            post_token_balance.append({
                "owner": str(post_token_bal.owner),
                "mint": str(post_token_bal.mint),
                "ui_amount": post_token_bal.ui_token_amount.ui_amount_string
            })
        total_balances["post_token_balance"] = post_token_balance
    total_balances["token_info"] = token_info
    return total_balances

def _collect_instruction_data(tx_result: GetTransactionResp, agent_pubkey: str) -> list[dict[str, any]]:
    instructions = tx_result.value.transaction.transaction.message.instructions
    ix_data = [_parse_balances(tx_result, agent_pubkey)]
    token_info = ix_data[0].get("token_info")
    print(ix_data)

    for ix in instructions:
        if not isinstance(ix, ParsedInstruction):
            continue

        if ix.program == "spl-memo":
            ix_data.append({
                "dest": ix.parsed,
                "amount": 0,
                "category": "message"
            })
            continue

        ix_parsed_info = ix.parsed["info"]
        ix_parsed_type = ix.parsed["type"]
        if (ix.program == "system" and ix_parsed_type == "transfer"):
            ix_data.append({
                "dest": ix_parsed_info["destination"],
                "amount": ix_parsed_info["lamports"],
                "category": "native_transfer"
            })
        if (ix.program == "spl-token" and (ix_parsed_type.startswith("transfer")) or ix_parsed_type in ["burn", "approve", "revoke"]):
            mint = ix_parsed_info.get("mint")
            if "amount" in ix_parsed_info:
                source = ix_parsed_info.get("source")
                decimals = int(token_info.get(mint) if mint else token_info.get(source))
                amount = Decimal(ix_parsed_info.get("amount")) / (10 ** decimals)
            elif "tokenAmount" in ix_parsed_info:
                amount = ix_parsed_info["tokenAmount"]["uiAmountString"]
            else:
                amount = "0"
            ix_data.append({
                "mint": mint,
                "dest": ix_parsed_info.get("destination", ix_parsed_info.get("delegate")),
                "amount": str(amount),
                "category": "spl_token_ops",
                "instruction": ix_parsed_type
            })
        if (ix.program == "spl-associated-token-account" and ix_parsed_type.startswith("create")):
            ix_data.append({
                "mint": ix_parsed_info.get("mint"),
                "account": ix_parsed_info["account"],
                "category": "create_account",
            })
    return ix_data

def calculate_query_reward(tx_result: Dict[str, Any], validation_conds: Dict[str, Any], agent_pubkey: str) -> float:
    if tx_result.get("type") != "queries":
        return 0

    reward = 0
    for rule in validation_conds:
        weight = int(rule["weight"])
        mint = rule.get("mint", None)
        owner = rule.get("owner", None)
        if rule["type"] == "query_balance" and "value" in tx_result:
            if mint and mint == tx_result.get("mint"):
                reward += weight
            elif owner and owner == tx_result.get("owner"):
                reward += weight
    print(f"reward: {reward}, result: {tx_result}")
    return reward

async def calculate_reward(tx_result: GetTransactionResp | Dict[str, Any], question: Dict[str, Any], agent_pubkey: str) -> float:
    print(f"question: {question}")
    validation_conds = question["validation"]["post_conditions"]
    question_category = question["subcategory"]
    if question_category == "queries":
        return (calculate_query_reward(tx_result, validation_conds, agent_pubkey)) / 100.0 * 1.0

    if tx_result.value.transaction.meta.err:
        return 0

    valid_ixs = _collect_instruction_data(tx_result, agent_pubkey)
    balances = valid_ixs[0]
    find_ix = next((ix for ix in valid_ixs if ix["category"] == question_category), None)
    if not find_ix:
        return 0
    print(f"find instruction: {find_ix}, {validation_conds}")
    
    reward = 0
    for rule in validation_conds:
        weight = int(rule["weight"])
        expected = rule.get("expected", "")
        tolerance = rule.get("tolerance", 0)
        percentage = rule.get("percentage", False)
        match rule["type"]:
            case "transaction_success":
                reward += weight

            case "address_check":
                if find_ix["dest"] == expected:
                    reward += weight
                else:
                    print(f"address_check error, {find_ix}")

            case "value_check":
                if percentage:
                    expected_lamports = Decimal(expected) * Decimal(balances["pre_balance"])
                else:
                    is_ui_amount = rule.get("is_ui_amount", False)
                    expected_lamports = Decimal(expected) * (1 if is_ui_amount else Decimal(1e9))
                if _between(Decimal(find_ix["amount"]), Decimal(expected_lamports), Decimal(tolerance * 1e9)):
                    reward += weight
                else:
                    print(f"value_check error, {find_ix}")

            case "message_check":
                find_ix = next((ix for ix in valid_ixs if ix["category"] == "message"), None)
                if find_ix and find_ix["dest"] == expected:
                    reward += weight
                else:
                    print(f"message_check error, {find_ix}")

            case "instruction_check":
                if find_ix and find_ix.get("instruction") == expected:
                    reward += weight
                else:
                    print(f"instruction_check error, {find_ix}")

            case "wsol_withdraw_increase":
                mint = rule.get("mint", None)
                owner = rule.get("owner", agent_pubkey)
                # Withdraw wsol, balance will increase
                pre_token_balance = next((b for b in balances["pre_token_balance"] if b["mint"] == mint and b["owner"] == owner), None)
                pre_token_amount = Decimal(0 if not pre_token_balance else pre_token_balance["ui_amount"]) * Decimal(1e9)
                if _between(balances["post_balance"], balances["pre_balance"] + int(pre_token_amount), int(tolerance * 1e9)):
                    reward += weight
                else:
                    print(f"wsol_withdraw_increase error, {pre_token_balance}")

            case "balance_change":
                mint = rule.get("mint", None)
                owner = rule.get("owner", agent_pubkey)
                compute = int(rule.get("compute", -1))
                if mint:
                    # Check spl token balance
                    pre_agent_token_blance = next((b for b in balances["pre_token_balance"] if b["mint"] == mint and b["owner"] == agent_pubkey), None)
                    pre_token_balance = next((b for b in balances["pre_token_balance"] if b["mint"] == mint and b["owner"] == owner), None)
                    post_token_balance = next((b for b in balances["post_token_balance"] if b["mint"] == mint and b["owner"] == owner), None)
                    pre_agent_token_amount = Decimal(0 if not pre_agent_token_blance else pre_agent_token_blance["ui_amount"])
                    pre_token_amount = Decimal(0 if not pre_token_balance else pre_token_balance["ui_amount"])
                    post_token_amount = Decimal(0 if not post_token_balance else post_token_balance["ui_amount"])
                    print(f"{owner}: {pre_token_amount} => {post_token_amount}")
                    # Check token balance
                    expected_amount = Decimal(expected)
                    if percentage:
                        expected_amount *= pre_agent_token_amount
                    expected_balance_after = pre_token_amount + (expected_amount * compute)
                    if _between(expected_balance_after, post_token_amount, Decimal(tolerance)):
                        reward += weight
                    else:
                        print("balance_change error")
                else:
                    # Check sol balance
                    if percentage:
                        expected_lamports = Decimal(expected) * Decimal(balances["pre_balance"])
                    else:
                        expected_lamports = Decimal(expected) * Decimal(1e9)
                    expected_balance_after = int(Decimal(balances["pre_balance"]) + (expected_lamports) * compute - balances["fee"])
                    if _between(expected_balance_after, balances["post_balance"], int(tolerance * 1e9)):
                        reward += weight
                    else:
                        print("balance_change error")

    print(f"reward: {reward}, balance: {balances}")
    return reward / 100.0 * 1.0

def _between(value, target, range):
    return target - range <= value <= target + range