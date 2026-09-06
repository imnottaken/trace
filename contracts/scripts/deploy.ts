import { ethers } from "hardhat";
import * as fs from "fs";
import * as path from "path";

export async function deployTraceProof() {
  console.log("==================================================");
  console.log("TRACE: Deploying TraceProof Smart Contract");
  console.log("==================================================");

  const [deployer] = await ethers.getSigners();
  const network = await ethers.provider.getNetwork();

  console.log(`Deployer address: ${deployer.address}`);
  const balance = await ethers.provider.getBalance(deployer.address);
  console.log(`Deployer balance: ${ethers.formatEther(balance)} ETH/POL`);
  console.log(`Target Network: ${network.name} (Chain ID: ${network.chainId})`);

  const TraceProofFactory = await ethers.getContractFactory("TraceProof");
  const traceProof = await TraceProofFactory.deploy();
  await traceProof.waitForDeployment();

  const contractAddress = await traceProof.getAddress();
  const deploymentTx = traceProof.deploymentTransaction();

  console.log("--------------------------------------------------");
  console.log(`TraceProof successfully deployed to: ${contractAddress}`);
  console.log(`Transaction Hash: ${deploymentTx?.hash}`);
  console.log("==================================================");

  // Export deployment record
  const deploymentInfo = {
    contractName: "TraceProof",
    address: contractAddress,
    chainId: Number(network.chainId),
    networkName: network.name,
    deployer: deployer.address,
    transactionHash: deploymentTx?.hash,
    deployedAt: new Date().toISOString(),
  };

  const deploymentsDir = path.join(__dirname, "../deployments");
  if (!fs.existsSync(deploymentsDir)) {
    fs.mkdirSync(deploymentsDir, { recursive: true });
  }
  const deploymentFilePath = path.join(
    deploymentsDir,
    `deployment-${network.chainId}.json`
  );
  fs.writeFileSync(deploymentFilePath, JSON.stringify(deploymentInfo, null, 2));
  console.log(`Saved deployment record to: ${deploymentFilePath}`);

  return { contractAddress, traceProof, deploymentInfo };
}

async function main() {
  await deployTraceProof();
}

if (require.main === module) {
  main().catch((error) => {
    console.error("Deployment failed:", error);
    process.exitCode = 1;
  });
}
