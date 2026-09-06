import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";
import * as path from "path";

dotenv.config({ path: path.resolve(__dirname, "../.env") });

const DEFAULT_DEV_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80";
const PRIVATE_KEY = process.env.EVM_PRIVATE_KEY || DEFAULT_DEV_KEY;
const POLYGON_AMOY_RPC = process.env.POLYGON_AMOY_RPC || "https://rpc-amoy.polygon.technology";

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.24",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      evmVersion: "cancun",
    },
  },
  networks: {
    hardhat: {
      chainId: 31337,
    },
    localhost: {
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
    polygonAmoy: {
      url: POLYGON_AMOY_RPC,
      chainId: 80002,
      accounts: [PRIVATE_KEY],
      gasPrice: "auto",
    },
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts",
  },
};

export default config;
