# Fund Manager Service
This service interacts with the Fund Manager contract for users to raise funds and send a proposal and funds are given to them according to the predefined conditions.

## Deployment Details
- Safe and Service have been deployed to Gnosis Tenderly Fork.
- Components and Agent have been minted to Ethereum Tenderly Fork.
- Fund Manager Contract Address: 0xbcf253651cfb56355a56aaed5c7cfbaf25dd04db
- Test Token: 0xe91d153e0b41518a2ce8dd3d7944fa863463a97d

## Overview
The Fund Manager contract accepts the proposal for fund and transfer the asked proposal amount to user's account. For testing purposes, custom ERC-20 tokens have been deployed. The service queries the contract to decides whether to to transfer funds or not based on this information.

## Current Logic
### Transaction Decision Logic
The service fetches the proposals of the funds and then decides whether to transact the funds or not based on predefined conditions:
  1. If the amount of proposal is within th range of max_proposal_aount and min_proposal_amount then:
     Transaction will take place and funds will be transfered to users's account.

  2. If the amount of proposal is within th range of max_proposal_aount and min_proposal_amount and not executed then:
     Transaction will not take place and it willl revert with "No proposals within the range; deciding to HOLD".

### Transaction Workflow

  1. An approval transaction is made (Gnosis Safe must approve the Fund Manager contract to transfer tokens from the Gnosis Safe to another address).
  2. A execute transaction is prepared.
  3. Both transactions are bundled into a multisend transaction.

### Future Enhancements
- Implementing complex logic in the service to implement a voting system where multiple stakeholders can vote on proposals before they are executed. This can enhance decision-making and decentralize authority
- Handling multiple tokens within the fund.

