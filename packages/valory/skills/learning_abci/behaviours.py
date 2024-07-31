# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2024 Valory AG
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

"""This package contains round behaviours of LearningAbciApp."""
from abc import ABC
from typing import Generator, Set, List, Type, cast, Optional, Dict, Any, Tuple, Union
from hexbytes import HexBytes
from packages.valory.contracts.fund_manager.contract import FundManagerContract
from packages.valory.contracts.erc20.contract import ERC20
from packages.valory.contracts.gnosis_safe.contract import (
    GnosisSafeContract,
    SafeOperation
)
from packages.valory.contracts.multisend.contract import (
    MultiSendContract,
    MultiSendOperation,
)
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseBehaviour,
)
from packages.valory.skills.learning_abci.models import Params, SharedState
from packages.valory.skills.learning_abci.payloads import (
    APICheckPayload,
    DecisionMakingPayload,
    TxPreparationPayload,
)
from packages.valory.skills.learning_abci.rounds import (
    APICheckRound,
    DecisionMakingRound,
    LearningAbciApp,
    SynchronizedData,
    TxPreparationRound,
    Event 
)
from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)
from packages.valory.skills.abstract_round_abci.io_.store import SupportedFiletype
import json


TX_DATA = b"0x"
SAFE_GAS = 0
MULTISEND_ADDRESS = "0xA238CBeb142c10Ef7Ad8442C6D1f9E89e07e7761"

class LearningBaseBehaviour(BaseBehaviour, ABC):  # pylint: disable=too-many-ancestors
    """Base behaviour for the learning_abci skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the synchronized data."""
        return cast(SynchronizedData, super().synchronized_data)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, super().params)

    @property
    def local_state(self) -> SharedState:
        """Return the state."""
        return cast(SharedState, self.context.state)


class APICheckBehaviour(LearningBaseBehaviour):  # pylint: disable=too-many-ancestors
    """APICheckBehaviour"""

    matching_round: Type[AbstractRound] = APICheckRound

    def async_act(self) -> Generator:
        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            sender = self.context.agent_address
            #price = yield from self.get_price()
            self.context.logger.info(f'{self.params.fund_manager_contract_address}')
            

            contract_response = yield from self.get_contract_api_response(
                performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
                contract_id=str(FundManagerContract.contract_id),
                contract_callable="get_all_proposals",
                contract_address=self.params.fund_manager_contract_address,
            )
            self.context.logger.info(
                f"These are the proposals: {contract_response}"
            )

            new_proposal = contract_response.state.body["data"]

            ipfs_hash = yield from self.send_to_ipfs(
                "new_proposal.json",
                {"new_proposal": new_proposal},
                filetype=SupportedFiletype.JSON
                )
            self.context.logger.info(f"The IPFS hash is : {ipfs_hash}")
            payload = APICheckPayload(sender=sender,ipfs_hash=ipfs_hash)

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()



class DecisionMakingBehaviour(LearningBaseBehaviour):  # pylint: disable=too-many-ancestors
    """DecisionMakingBehaviour"""

    matching_round: Type[AbstractRound] = DecisionMakingRound
    
    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local(): 
            decision, proposal_info = yield from self.make_transaction_decision()
            
            self.context.logger.info(f"DECISION MADE: {decision}")
            sender = self.context.agent_address
            payload = DecisionMakingPayload(
                sender=sender,
                content=json.dumps(
                    {"decision": decision, "proposal_info": proposal_info}, sort_keys=True
                ),
            )
        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()
    
    def make_transaction_decision(self) -> Generator[None, None, Tuple[str,Dict[str,int]]]:
        """Download proposals from IPFS, check condition, and make a decision."""
        
        # Fetch proposals from IPFS
        proposals_ipfs_hash = self.synchronized_data.ipfs_hash
       
        proposals = yield from self.fetch_proposals_from_ipfs(proposals_ipfs_hash)
        contract_response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_id=str(FundManagerContract.contract_id),
            contract_callable="get_all_proposals",
            contract_address=self.params.fund_manager_contract_address,
        )
        
        self.context.logger.info(f"Proposals are: { contract_response}")
        proposals = contract_response.state.body["data"]
        
        self.context.logger.info(f"Maximum amount: {self.params.max_proposal_amount} , Minimum amount {self.params.min_proposal_amount}")
        for proposal in proposals:
            proposal_amount = int(proposal[2])
            self.context.logger.info(f"Proposal amount: {proposal_amount}")
            if (
                (self.params.min_proposal_amount
                < proposal_amount
                < self.params.max_proposal_amount) and proposal[3] != True
            ):
                
                return Event.TRANSACT.value, {
                    "proposal_id": proposal[0],
                    "proposal_amount": proposal[2]
                }
            

        self.context.logger.info(
            "No unexecuted proposals within the range; deciding to HOLD"
        )
        return Event.DONE.value, {}
            

        

    def fetch_proposals_from_ipfs(self, ipfs_hash: str) -> Generator[None, None, list[dict]]:
        """Fetch proposals from IPFS."""
        proposals=yield from self.get_from_ipfs(
            self.synchronized_data.ipfs_hash, filetype=SupportedFiletype.JSON
        )
        return proposals

    
        
class TxPreparationBehaviour(
    LearningBaseBehaviour
):  # pylint: disable=too-many-ancestors
    """TxPreparationBehaviour"""

    matching_round: Type[AbstractRound] = TxPreparationRound
    ETHER_VALUE = 0

    def async_act(self) -> Generator:
        """Do the act, supporting asynchronous execution."""

        with self.context.benchmark_tool.measure(self.behaviour_id).local():
            update_proposal_payload = yield from self.get_proposal_update()

        with self.context.benchmark_tool.measure(self.behaviour_id).consensus():
            payload = TxPreparationPayload(
                self.context.agent_address,
                update_proposal_payload
            )
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def get_proposal_update(self) -> Generator[None, None, str]:
        """
        Prepare the necessary transactions for executing a proposal.
        """

        transactions = yield from self._build_approve_and_execute_txns()
        if transactions is None:
            return "{}"
        
        payload_data = yield from self._get_multisend_tx(transactions)
        self.context.logger.info(f"MULTISEND TRANSACTIONS: {payload_data}")
        if payload_data is None:
            return "{}"
        return payload_data

    def _build_approve_txn(self) -> Generator[None, None, Optional[bytes]]:
        self.context.logger.info(f"contract address:{self.params.fund_manager_contract_address}")
        self.context.logger.info(f"amount:{self.synchronized_data.proposal_amount}")

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_id=str(ERC20.contract_id),
            contract_callable="build_approval_tx",
            contract_address=self.params.fund_token,
            spender=self.params.fund_manager_contract_address,
            amount=self.synchronized_data.proposal_amount
        )
        

        self.context.logger.info(f"APPROVE TXN: {response}")

        if response.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                f"TxPreparationBehaviour says: Couldn't get tx data for the approval txn. "
                f"Expected response performative {ContractApiMessage.Performative.STATE.value}, "  # type: ignore
                f"received {response.performative.value}."
            )
            return None
    
        data_str = cast(str, response.state.body["data"])[2:]
        data = bytes.fromhex(data_str)
        return data
    
    def _build_execute_txn(self) -> Generator[None, None, Optional[bytes]]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_id=str(FundManagerContract.contract_id),
            contract_callable="get_execute_proposal_tx",
            contract_address=self.params.fund_manager_contract_address,
            proposal_id=self.synchronized_data.proposal_id
        )

        self.context.logger.info(f"EXECUTE TXN: {response}")

        if response.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                f"TxPreparationBehaviour says: Couldn't get tx data for the execute txn. "
                f"Expected response performative {ContractApiMessage.Performative.STATE.value}, "  # type: ignore
                f"received {response.performative.value}."
            )
            return None

        data_str = cast(str, response.state.body["data"])[2:]
        data = bytes.fromhex(data_str)
        return data
    
    def _build_approve_and_execute_txns(self) -> Generator[None, None, Optional[List[bytes]]]:
        transactions: List[bytes] = []

        approve_tx_data = yield from self._build_approve_txn()
        if approve_tx_data is None:
            return None      
        transactions.append(approve_tx_data)

        execute_tx_data = yield from self._build_execute_txn()
        if execute_tx_data is None:
            return None      
        transactions.append(execute_tx_data)

        return transactions

    def _get_safe_tx_hash(self, data: bytes, to_address: str, is_multisend: bool = False) -> Generator[None, None, Optional[str]]:
        """
        Prepares and returns the safe tx hash.

        This hash will be signed later by the agents, and submitted to the safe contract.
        Note that this is the transaction that the safe will execute, with the provided data.

        :param data: the safe tx data. This is the data of the function being called.
        :return: the tx hash
        """
        self.context.logger.info(f"Preparing to call contract with the following parameters:")
        self.context.logger.info(f"Data: {data}")
        self.context.logger.info(f"To Address: {to_address}")
        self.context.logger.info(f"Is Multisend: {is_multisend}")
        
        contract_api_kwargs = {
            "performative": ContractApiMessage.Performative.GET_STATE,  # type: ignore
            "contract_address": self.synchronized_data.safe_contract_address,  # the safe contract address
            "contract_id": str(GnosisSafeContract.contract_id),
            "contract_callable": "get_raw_safe_transaction_hash",
            "to_address": to_address,
            "value": self.ETHER_VALUE,
            "data": data,
            "safe_tx_gas": SAFE_GAS,
        }
        
        if is_multisend:
            contract_api_kwargs["operation"] = SafeOperation.DELEGATE_CALL.value

        response = yield from self.get_contract_api_response(**contract_api_kwargs)
        self.context.logger.info(f"RESPONSE:{response}")

        if response.performative != ContractApiMessage.Performative.STATE:
            self.context.logger.error(
                f"TxPreparationBehaviour says: Couldn't get safe hash. "
                f"Expected response performative {ContractApiMessage.Performative.STATE.value}, "  # type: ignore
                f"received {response.performative.value}."
            )
            return None

        # strip "0x" from the response hash
        tx_hash = cast(str, response.state.body["tx_hash"])[2:]
        return tx_hash

    def _get_multisend_tx(self, txs: List[bytes]) -> Generator[None, None, Optional[str]]:
        """Given a list of transactions, bundle them together in a single multisend tx."""
        multi_send_txs = []

        multi_send_approve_tx = self._to_multisend_format(txs[0], self.params.fund_token)
        multi_send_txs.append(multi_send_approve_tx)

        multi_send_execute_tx = self._to_multisend_format(txs[1], self.params.fund_manager_contract_address)
        multi_send_txs.append(multi_send_execute_tx)

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,  # type: ignore
            contract_address=MULTISEND_ADDRESS,
            contract_id=str(MultiSendContract.contract_id),
            contract_callable="get_tx_data",
            multi_send_txs=multi_send_txs,
        )

        self.context.logger.info(f"PREPARED MULTISEND TXN: {response}")

        if response.performative != ContractApiMessage.Performative.RAW_TRANSACTION:
            self.context.logger.error(
                f"Couldn't compile the multisend tx. "
                f"Expected response performative {ContractApiMessage.Performative.RAW_TRANSACTION.value}, "  # type: ignore
                f"received {response.performative.value}."
            )
            return None

        # strip "0x" from the response
        multisend_data_str = cast(str, response.raw_transaction.body["data"])[2:]
        tx_data = bytes.fromhex(multisend_data_str)
        tx_hash = yield from self._get_safe_tx_hash(tx_data, MULTISEND_ADDRESS, is_multisend=True)
        
        if tx_hash is None:
            return None

        payload_data = hash_payload_to_hex(
            safe_tx_hash=tx_hash,
            ether_value=self.ETHER_VALUE,
            safe_tx_gas=SAFE_GAS,
            operation=SafeOperation.DELEGATE_CALL.value,
            to_address=MULTISEND_ADDRESS,
            data=tx_data,
        )
        return payload_data

    def _to_multisend_format(self, single_tx: bytes, to_address: str) -> Dict[str, Any]:
        """This method puts tx data from a single tx into the multisend format."""
        multisend_format = {
            "operation": MultiSendOperation.CALL,
            "to": to_address,
            "value": self.ETHER_VALUE,
            "data": HexBytes(single_tx),
        }
        return multisend_format
 
class LearningRoundBehaviour(AbstractRoundBehaviour):
    """LearningRoundBehaviour"""

    initial_behaviour_cls = APICheckBehaviour
    abci_app_cls = LearningAbciApp  # type: ignore
    behaviours: Set[Type[BaseBehaviour]] = [  # type: ignore
        APICheckBehaviour,
        DecisionMakingBehaviour,
        TxPreparationBehaviour,
    ]
