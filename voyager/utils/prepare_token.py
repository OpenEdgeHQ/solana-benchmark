import subprocess
import json
import base64
import base58
import gymnasium as gym
import asyncio
from contextlib import asynccontextmanager
import logging
import json
import shutil
import os
import signal
from dotenv import load_dotenv
from os.path import dirname, join

from solders.system_program import transfer, TransferParams, create_nonce_account
from solders.message import MessageV0, to_bytes_versioned
from solders.pubkey import Pubkey
from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from spl.token.instructions import get_associated_token_address, sync_native, SyncNativeParams
from solders.transaction import Transaction
from solders.message import Message
from solana.rpc.api import Client
from solders.keypair import Keypair

USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

def _create_and_mint_nft(secret: str):
    logging.info("Prepare testing NFTs")
    command = ["bun", "voyager/skill_runner/create_nft.ts", secret]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        encoding='utf-8'
    )
    # parse the last line of the output
    nft_mints = json.loads(result.stdout.strip("\n").split("\n")[-1])
    if result.stderr:
        logging.error(f"_create_and_mint_nft error: {result.stderr}")
    logging.info(f"NTF Tokens: {nft_mints}")
    return nft_mints
    
def _wrap_sol(agent_keypair: Keypair, syncClient: Client, lamports: int):
    logging.info(f"Prepare warpped SOLs")
    owner = agent_keypair.pubkey()
    WSOL_MINT = Pubkey.from_string("So11111111111111111111111111111111111111112")
    wsol_ata = get_associated_token_address(owner, WSOL_MINT)
    # Create wsol account
    token = Token(conn=syncClient, pubkey=WSOL_MINT, program_id=TOKEN_PROGRAM_ID, payer=agent_keypair)
    token.create_associated_token_account(owner=owner)
    # Transfer sol to wsol account
    msg = Message([
        transfer(TransferParams(from_pubkey=owner, to_pubkey=wsol_ata, lamports=lamports)),
        sync_native(SyncNativeParams(program_id=TOKEN_PROGRAM_ID, account=wsol_ata))
    ])
    blockhash = syncClient.get_latest_blockhash().value.blockhash
    tx = Transaction(from_keypairs=[agent_keypair], message=msg, recent_blockhash=blockhash)
    syncClient.send_transaction(tx)

def _mint_spl_token(agent_keypair: Keypair, syncClient: Client, num = 5):
    logging.info(f"Prepare SPL tokens")
    token_mints = [USDC_MINT, USDT_MINT]
    owner = agent_keypair.pubkey()
    # for i in range(num):
    #     DECIMALS = 6
    #     # create token mint
    #     token = Token.create_mint(
    #         conn=syncClient,
    #         payer=agent_keypair,
    #         mint_authority=owner,
    #         decimals=DECIMALS,
    #         program_id=TOKEN_PROGRAM_ID,
    #     )
    #     # mint 100M token
    #     amount = 100_000_000 * (10 ** DECIMALS)
    #     receiver_token_account = token.create_associated_token_account(owner)
    #     token.mint_to(dest=receiver_token_account, mint_authority=agent_keypair, amount=amount)
    #     token_mints.append(str(token.pubkey))
    _prepare_swap_token(str(owner), USDT_MINT, syncClient)
    _prepare_swap_token(str(owner), USDC_MINT, syncClient)
    logging.info(f"SPL Tokens: {token_mints}")
    return token_mints

def _prepare_swap_token(owner: str, mint: str, syncClient: Client):
    params = [owner, mint, {"amount": 10000000000}, str(TOKEN_PROGRAM_ID)]
    body = {"jsonrpc": "2.0", "id": 1, "method": "surfnet_setTokenAccount", "params": params}
    syncClient._provider.session.post(syncClient._provider.endpoint_uri, json=body)
