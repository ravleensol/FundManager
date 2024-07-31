from typing import Any, Dict, Optional, List, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea_ledger_ethereum import LedgerApi

PUBLIC_ID = PublicId.from_str("valory/fund_manager:0.1.0")

class FundManagerContract(Contract):
    contract_id = PUBLIC_ID

    @classmethod
    def get_execute_proposal_tx(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        proposal_id: int
    ) -> Dict[str, any]:
        contract_instance = cls.get_instance(ledger_api, contract_address)
        tx_data = contract_instance.encodeABI(
            fn_name="executeProposal",
            args=[
                proposal_id
            ],
        )
        return dict(
            data=tx_data,
        )
    
    @classmethod
    def get_all_proposals(
        cls,
        ledger_api: LedgerApi,
        contract_address: str
    ) -> Dict[str,any]:
        contract_instance = cls.get_instance(ledger_api, contract_address)
        proposals = contract_instance.functions.getAllProposals().call()
        print(proposals)
        print(contract_address)
        return dict(data=proposals)
        
