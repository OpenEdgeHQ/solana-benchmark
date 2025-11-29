import { createNft, mplTokenMetadata, transferV1 } from '@metaplex-foundation/mpl-token-metadata'
import { createUmi } from '@metaplex-foundation/umi-bundle-defaults'
import { createSignerFromKeypair, generateSigner, keypairIdentity, percentAmount, PublicKey, sol, Umi } from '@metaplex-foundation/umi';
import { mockStorage } from '@metaplex-foundation/umi-storage-mock';
import { base58 } from '@metaplex-foundation/umi/serializers';

// example: bun create_nft.ts [base58 private key]
async function mintAgentNft(secret: string) {
    const rpc = 'http://127.0.0.1:8899';
    const umi = createUmi(rpc); 
    const creatorWallet = umi.eddsa.createKeypairFromSecretKey(base58.serialize(secret));
    const creator = createSignerFromKeypair(umi, creatorWallet);
    console.log(creator.publicKey, await umi.rpc.getBalance(creator.publicKey))
    umi.use(keypairIdentity(creator));
    umi.use(mplTokenMetadata());
    umi.use(mockStorage());
    const nfts = []
    for (let i = 0; i < 10; i++) {
        nfts.push(await mintOneNft(umi, creator.publicKey))
    }
    console.log(JSON.stringify(nfts))
}

async function mintOneNft(umi: Umi, creator: PublicKey) {
    try {
        const mint = generateSigner(umi);
        await createNft(umi, {
            mint,
            name: "Divinity - DevNet",
            symbol: "DIV",
            uri: "https://arweave.net/lafoms3egQiVeboVVSsgIXRH14DiyxmKLwzD_EWiKv8",
            sellerFeeBasisPoints: percentAmount(1),
            creators: [{ address: creator, verified: true, share: 100 }],
        }).sendAndConfirm(umi)
        return mint.publicKey
    } catch (e) {
        throw e;
    }
}

const [,, secret] = process.argv
mintAgentNft(secret)