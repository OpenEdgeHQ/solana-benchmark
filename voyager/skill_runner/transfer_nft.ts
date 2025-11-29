import { createNft, mplTokenMetadata, TokenStandard, transferV1 } from '@metaplex-foundation/mpl-token-metadata'
import { createUmi } from '@metaplex-foundation/umi-bundle-defaults'
import { createSignerFromKeypair, generateSigner, keypairIdentity, percentAmount, publicKey, sol, Umi } from '@metaplex-foundation/umi';
import { mockStorage } from '@metaplex-foundation/umi-storage-mock';
import { base58 } from '@metaplex-foundation/umi/serializers';


async function transferNFT() {
    const rpc = 'http://127.0.0.1:8899';
    const umi = createUmi(rpc);
    const pk = "4VJvjAxyhuXDJqoAzPGyFacsPNrfmP4PuPmduVtnS2RskBKTezAmD9LXTxpXenAQntNjt4xBdmbvNU5XPsYU8cN1"
    const mint = publicKey("77JG7B7ysyP2Sz7sJfJ8z96gXhYyeMDkq77vMzqDuXX1")
    const creatorWallet = umi.eddsa.createKeypairFromSecretKey(base58.serialize(pk));
    const currentOwner = createSignerFromKeypair(umi, creatorWallet);
    umi.use(mplTokenMetadata());
    umi.use(keypairIdentity(currentOwner));
    const resp = await transferV1(umi, {
        mint,
        authority: currentOwner,
        tokenOwner: currentOwner.publicKey,
        destinationOwner: publicKey("9PjYzLqLu9hfKyas52rCxiHaoJ66XGUQPuQh49vvGnQg"),
        tokenStandard: TokenStandard.NonFungible,
    }).sendAndConfirm(umi)
    console.log(resp.signature)
}

transferNFT()