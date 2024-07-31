#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2024 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------


"""Updates fetched agent with correct config"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


def main() -> None:
    """Main"""
    load_dotenv()

    with open(Path("learning_agent", "aea-config.yaml"), "r", encoding="utf-8") as file:
        config = list(yaml.safe_load_all(file))

        # Ledger RPCs
        if os.getenv("ETHEREUM_LEDGER_RPC"):
            config[2]["config"]["ledger_apis"]["ethereum"][
                "address"
            ] = f"${{str:{os.getenv('ETHEREUM_LEDGER_RPC')}}}"

        if os.getenv("GNOSIS_LEDGER_RPC"):
            config[2]["config"]["ledger_apis"]["gnosis"][
                "address"
            ] = f"${{str:{os.getenv('GNOSIS_LEDGER_RPC')}}}"

        # Params
        if os.getenv("FUND_MANAGER_CONTRACT_ADDRESS"):
            config[-1]["models"]["params"]["args"][
                "fund_manager_contract_address"
            ] = f"${{str:{os.getenv('FUND_MANAGER_CONTRACT_ADDRESS')}}}"  # type: ignore

        if os.getenv("FUND_TOKEN"):
            config[-1]["models"]["params"]["args"][
                "fund_token"
            ] = f"${{str:{os.getenv('FUND_TOKEN')}}}"  # type: ignore

        if os.getenv("TRANSFER_TARGET_ADDRESS"):
            config[-1]["models"]["params"]["args"][
                "transfer_target_address"
            ] = f"${{str:{os.getenv('TRANSFER_TARGET_ADDRESS')}}}"  # type: ignore

        if os.getenv("COINGECKO_API_KEY"):
            config[-1]["models"]["params"]["args"][
                "coingecko_api_key"
            ] = f"${{str:{os.getenv('COINGECKO_API_KEY')}}}"  # type: ignore

        if os.getenv("SAFE_CONTRACT_ADDRESS"):
            config[-1]["models"]["params"]["args"]["setup"][
                "safe_contract_address"
            ] = f"${{str:{os.getenv('SAFE_CONTRACT_ADDRESS')}}}" 
        
        if os.getenv("ALL_PARTICIPANTS"):
            config[-1]["models"]["params"]["args"]["setup"][
                "all_participants"
            ] = f"${{list:{os.getenv('ALL_PARTICIPANTS')}}}" 
        
        if os.getenv("MULTISEND_ADDRESS"):
            config[-1]["models"]["params"]["args"][
                "multisend_address"
            ] = f"${{str:{os.getenv('MULTISEND_ADDRESS')}}}"  # type: ignore

        if os.getenv("MIN_DEVIATION_THRESHOLD"):
            config[-1]["models"]["params"]["args"][
                "min_deviation_threshold"
                ] = f"${{list:{os.getenv('MIN_DEVIATION_THRESHOLD')}}}"

        if os.getenv("MIN_PROPOSAL_AMOUNT"):
            config[-1]["models"]["params"]["args"][
                "min_proposal_amount"
                ] = f"${{list:{os.getenv('MIN_PROPOSAL_AMOUNT')}}}"
        
        if os.getenv("MAX_PROPOSAL_AMOUNT"):
            config[-1]["models"]["params"]["args"][
                "max_proposal_amount"
                ] = f"${{list:{os.getenv('MAX_PROPOSAL_AMOUNT')}}}"

    with open(Path("learning_agent", "aea-config.yaml"), "w", encoding="utf-8") as file:
        yaml.dump_all(config, file, sort_keys=False)


if __name__ == "__main__":
    main()
