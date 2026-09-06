import { ethers, run } from "hardhat";
import * as fs from "fs";
import * as path from "path";

export async function exportAbi() {
  console.log("==================================================");
  console.log("TRACE: Exporting Contract ABI & Deployment Config");
  console.log("==================================================");

  // Ensure contracts are compiled
  const artifactPath = path.join(
    __dirname,
    "../artifacts/contracts/TraceProof.sol/TraceProof.json"
  );

  if (!fs.existsSync(artifactPath)) {
    console.log("Artifacts not found, running compile first...");
    await run("compile");
  }

  const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf-8"));

  // Check for existing deployment records
  const network = await ethers.provider.getNetwork();
  const deploymentsDir = path.join(__dirname, "../deployments");
  const deploymentFilePath = path.join(
    deploymentsDir,
    `deployment-${network.chainId}.json`
  );

  let deployedAddress = process.env.CONTRACT_ADDRESS || "0x5FbDB2315678afecb367f032d93F642f64180aa3";
  let transactionHash = "";
  let deployedAt = new Date().toISOString();

  if (fs.existsSync(deploymentFilePath)) {
    try {
      const depData = JSON.parse(fs.readFileSync(deploymentFilePath, "utf-8"));
      deployedAddress = depData.address || deployedAddress;
      transactionHash = depData.transactionHash || "";
      deployedAt = depData.deployedAt || deployedAt;
      console.log(`Loaded existing deployment for chain ${network.chainId}: ${deployedAddress}`);
    } catch (e) {
      console.warn("Could not parse existing deployment file:", e);
    }
  }

  const exportPayload = {
    contractName: "TraceProof",
    address: deployedAddress,
    chainId: Number(network.chainId),
    networkName: network.name,
    transactionHash,
    deployedAt,
    abi: artifact.abi,
  };

  const targetPaths = [
    path.resolve(__dirname, "../../backend/app/blockchain/abi/TraceProof.json"),
    path.resolve(__dirname, "../../frontend/lib/contracts/TraceProof.json"),
  ];

  for (const targetPath of targetPaths) {
    const dir = path.dirname(targetPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(targetPath, JSON.stringify(exportPayload, null, 2), "utf-8");
    console.log(`Successfully exported ABI artifact to: ${targetPath}`);
  }

  console.log("==================================================");
  console.log("ABI export complete.");
  console.log("==================================================");
  return exportPayload;
}

async function main() {
  await exportAbi();
}

if (require.main === module) {
  main().catch((error) => {
    console.error("ABI Export failed:", error);
    process.exitCode = 1;
  });
}
