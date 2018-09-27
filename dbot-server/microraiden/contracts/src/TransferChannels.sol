pragma solidity ^0.4.20;

import "./lib/ECVerify.sol";

/*
 * Interfaces
 */

/// @dev The contract as receiver must implement these functions
contract ReceiverContract {
/// @notice Called to get owner of the Contract
/// @return Address of the owner
    function getOwner() public returns (address);
}

/// @title Transfer Channels Contract.
contract TransferChannels {

    /*
     *  Data structures
     */
    // Contract semantic version
    string public constant version = '1.0.0';

    // Number of blocks to wait from an uncooperativeClose initiated by the sender
    // in order to give the receiver a chance to respond with a balance proof in case the sender cheats.
    // After the challenge period, the sender can settle and delete the channel.
    uint32 public constant challengePeriod = 5000;


    // We temporarily limit total deposits in a channel to 10000 ATN with 18 decimals.
    uint256 public constant channel_deposit_bugbounty_limit = 10 ** 18 * 10000;

    mapping (bytes32 => Channel) public channels;
    mapping (bytes32 => ClosingRequest) public closing_requests;
    mapping (bytes32 => uint256) public withdrawn_balances;

    struct Channel {
        // uint256 is the maximum uint size needed for deposit based on 2.1 * 10^8 * 10^18 totalSupply.
        uint256 deposit;
        // Block number at which the channel was opened.
        uint32 open_block_number;
    }

    struct ClosingRequest {
        // Balance owed by the sender when closing the channel.
        uint256 closing_balance;
        // Block number at which the challenge period ends, in case it has been initiated.
        uint32 settle_block_number;
    }

    /*
     *  Events
     */

    event ChannelCreated(
        address indexed _sender_address,
        address indexed _receiver_address,
        uint256 _deposit);
    event ChannelToppedUp (
        address indexed _sender_address,
        address indexed _receiver_address,
        uint32 indexed _open_block_number,
        uint256 _added_deposit);
    event ChannelCloseRequested(
        address indexed _sender_address,
        address indexed _receiver_address,
        uint32 indexed _open_block_number,
        uint256 _balance);
    event ChannelSettled(
        address indexed _sender_address,
        address indexed _receiver_address,
        uint32 indexed _open_block_number,
        uint256 _balance,
        uint256 _receiver_remaining_balance);
    event ChannelWithdraw(
        address indexed _sender_address,
        address indexed _receiver_address,
        uint32 indexed _open_block_number,
        uint256 _withdrawn_balance);

    /*
     *  External functions
     */

    /// @notice Create a channel between `msg.sender` and `_receiver_address` and transfer `msg.value` to this contract as deposit in the channel.
    /// @param _receiver_address The address of the receiver.
    function createChannel(address _receiver_address) external payable {
        createChannelPrivate(msg.sender, _receiver_address, msg.value);
    }

    /// @notice Increase the channel deposit with `msg.value`.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    function topUp(
        address _receiver_address,
        uint32 _open_block_number)
        payable
        external
    {
        updateInternalBalanceStructs(
            msg.sender,
            _receiver_address,
            _open_block_number,
            msg.value
        );
    }

    /// @notice Allows channel receiver to withdraw balance.
    /// @param _open_block_number The block number at which the channel was created.
    /// @param _balance Partial or total amount of balance owed by the sender to the receiver.
    /// Has to be smaller or equal to the channel deposit. Has to match the balance value from `_balance_msg_sig`
    /// @param _balance_msg_sig The balance message signed by the sender.
    /// @return withdrawed balance
    function withdraw(
        uint32 _open_block_number,
        uint256 _balance,
        bytes _balance_msg_sig)
        external
        returns (uint256)
    {
        require(_balance > 0);

        // Derive sender address from signed balance proof
        address sender_address = extractBalanceProofSignature(
            msg.sender,
            _open_block_number,
            _balance,
            _balance_msg_sig
        );

        bytes32 key = getKey(sender_address, msg.sender, _open_block_number);

        // Make sure the channel exists
        require(channels[key].open_block_number > 0);

        // Make sure the channel is not in the challenge period
        require(closing_requests[key].settle_block_number == 0);

        require(_balance <= channels[key].deposit);
        require(withdrawn_balances[key] < _balance);

        uint256 remaining_balance = _balance - withdrawn_balances[key];
        withdrawn_balances[key] = _balance;

        // Send the remaining balance to the receiver
        msg.sender.transfer(remaining_balance);

        emit ChannelWithdraw(sender_address, msg.sender, channels[key].open_block_number, remaining_balance);
        return remaining_balance;
    }


    /// @notice Called by the sender or receiver with all the needed signatures to close and settle the channel immediately.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    /// @param _balance The amount of balance owed by the sender to the receiver.
    /// @param _balance_msg_sig The balance message signed by the sender.
    /// @param _closing_sig The receiver's signed balance message, containing the sender's address.
    /// If the receiver is a contract, it should be signed by the constract's owner
    function cooperativeClose(
        address _receiver_address,
        uint32 _open_block_number,
        uint256 _balance,
        bytes _balance_msg_sig,
        bytes _closing_sig)
        external
    {
        // Derive sender address from signed balance proof
        address sender = extractBalanceProofSignature(
            _receiver_address,
            _open_block_number,
            _balance,
            _balance_msg_sig
        );

        // Derive receiver address from closing signature
        address signer = extractClosingSignature(
            sender,
            _open_block_number,
            _balance,
            _closing_sig
        );

        // If the receiver is a contract, the `_closing_sig` should be signed by it's owner
        if (isContract(_receiver_address)) {
            require(signer == ReceiverContract(_receiver_address).getOwner());
        } else {
            require(signer == _receiver_address);
        }

        // Both signatures have been verified and the channel can be settled immediately.
        settleChannel(sender, _receiver_address, _open_block_number, _balance);
    }

    /// @notice Sender requests the closing of the channel and starts the challenge period.
    /// This can only happen once.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    /// @param _balance The amount of blance owed by the sender to the receiver.
    function uncooperativeClose(
        address _receiver_address,
        uint32 _open_block_number,
        uint256 _balance)
        external
    {
        bytes32 key = getKey(msg.sender, _receiver_address, _open_block_number);

        require(channels[key].open_block_number > 0);
        require(closing_requests[key].settle_block_number == 0);
        require(_balance <= channels[key].deposit);

        // Mark channel as closed
        closing_requests[key].settle_block_number = uint32(block.number) + challengePeriod;
        require(closing_requests[key].settle_block_number > block.number);
        closing_requests[key].closing_balance = _balance;
        emit ChannelCloseRequested(msg.sender, _receiver_address, channels[key].open_block_number, _balance);
    }


    /// @notice Function called by the sender after the challenge period has ended, in order to
    /// settle and delete the channel, in case the receiver has not closed the channel himself.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    function settle(address _receiver_address, uint32 _open_block_number) external {
        bytes32 key = getKey(msg.sender, _receiver_address, _open_block_number);

        // Make sure an uncooperativeClose has been initiated
        require(closing_requests[key].settle_block_number > 0);

        // Make sure the challengePeriod has ended
	    require(block.number > closing_requests[key].settle_block_number);

        settleChannel(msg.sender, _receiver_address, _open_block_number, closing_requests[key].closing_balance
        );
    }

    /// @notice Retrieving information about a channel.
    /// @param _sender_address The address of the sender.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    /// @return Channel information: key, deposit, open_block_number, settle_block_number, closing_balance, withdrawn balance).
    function getChannelInfo(
        address _sender_address,
        address _receiver_address,
        uint32 _open_block_number)
        external
        view
        returns (bytes32, uint256, uint32, uint256, uint256)
    {
        bytes32 key = getKey(_sender_address, _receiver_address, _open_block_number);
        require(channels[key].open_block_number > 0);

        return (
            key,
            channels[key].deposit,
            // channels[key].open_block_number,
            closing_requests[key].settle_block_number,
            closing_requests[key].closing_balance,
            withdrawn_balances[key]
        );
    }

    /*
     *  Public functions
     */

    /// @notice Returns the sender address extracted from the balance proof.
    /// work with eth_signTypedData https://github.com/ethereum/EIPs/pull/712.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    /// @param _balance The amount of balance.
    /// @param _balance_msg_sig The balance message signed by the sender.
    /// @return Address of the balance proof signer.
    function extractBalanceProofSignature(
        address _receiver_address,
        uint32 _open_block_number,
        uint256 _balance,
        bytes _balance_msg_sig)
        public
        view
        returns (address)
    {
        // The variable names from below will be shown to the sender when signing the balance proof.
        // The hashed strings should be kept in sync with this function's parameters (variable names and types).
        // ! Note that EIP712 might change how hashing is done, triggering a new contract deployment with updated code.
        bytes32 message_hash = keccak256(
            keccak256(
                'string message_id',
                'address receiver',
                // 'uint32 block_created',
                'uint256 balance',
                'address contract'
            ),
            keccak256(
                'Sender balance proof signature',
                _receiver_address,
                // _open_block_number,
                _balance,
                address(this)
            )
        );

        // Derive address from signature
        address signer = ECVerify.ecverify(message_hash, _balance_msg_sig);
        return signer;
    }

    /// @dev Returns the receiver address extracted from the closing signature.
    /// Works with eth_signTypedData https://github.com/ethereum/EIPs/pull/712.
    /// @param _sender_address The address of the sender.
    /// @param _open_block_number The block number at which the channel was created.
    /// @param _balance The amount of balance.
    /// @param _closing_sig The receiver's signed balance message, containing the sender's address.
    /// @return Address of the closing signature signer.
    function extractClosingSignature(
        address _sender_address,
        uint32 _open_block_number,
        uint256 _balance,
        bytes _closing_sig)
        public
        view
        returns (address)
    {
        // The variable names from below will be shown to the sender when signing the balance proof.
        // The hashed strings should be kept in sync with this function's parameters (variable names and types).
        // ! Note that EIP712 might change how hashing is done, triggering a
        // new contract deployment with updated code.
        bytes32 message_hash = keccak256(
            keccak256(
                'string message_id',
                'address sender',
                // 'uint32 block_created',
                'uint256 balance',
                'address contract'
            ),
            keccak256(
                'Receiver closing signature',
                _sender_address,
                // _open_block_number,
                _balance,
                address(this)
            )
        );

        // Derive address from signature
        address signer = ECVerify.ecverify(message_hash, _closing_sig);
        return signer;
    }

    /// @notice Returns the unique channel identifier used in the contract.
    /// @param _sender_address The address of the sender.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    /// @return Unique channel identifier.
    function getKey(
        address _sender_address,
        address _receiver_address,
        uint32 _open_block_number)
        public
        pure
        returns (bytes32 data)
    {
        // TMP: ignore _open_block_number as channel identifier, so that only one channel allowed
        return keccak256(_sender_address, _receiver_address);
    }

    /*
     *  Private functions
     */

    /// @dev Creates a new channel between a sender and a receiver.
    /// @param _sender_address The address of the sender.
    /// @param _receiver_address The address of the receiver.
    function createChannelPrivate(
        address _sender_address,
        address _receiver_address,
        uint256 _deposit)
        private
    {
        require(_deposit <= channel_deposit_bugbounty_limit);

        uint32 open_block_number = uint32(block.number);

        // Create unique identifier from sender, receiver and current block number
        bytes32 key = getKey(_sender_address, _receiver_address, open_block_number);

        require(channels[key].deposit == 0);
        require(channels[key].open_block_number == 0);
        require(closing_requests[key].settle_block_number == 0);

        // Store channel information
        channels[key] = Channel({deposit: _deposit, open_block_number: open_block_number});
        emit ChannelCreated(_sender_address, _receiver_address, _deposit);
    }

    /// @dev Updates internal balance Structures when the sender adds tokens to the channel.
    /// @param _sender_address The address of the sender.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    /// @param _added_deposit The added token deposit with which the current deposit is increased.
    function updateInternalBalanceStructs(
        address _sender_address,
        address _receiver_address,
        uint32 _open_block_number,
        uint256 _added_deposit)
        private
    {
        require(_added_deposit > 0);
        require(_open_block_number > 0);

        bytes32 key = getKey(_sender_address, _receiver_address, _open_block_number);

        require(channels[key].open_block_number > 0);
        require(closing_requests[key].settle_block_number == 0);
        require(channels[key].deposit + _added_deposit <= channel_deposit_bugbounty_limit);

        channels[key].deposit += _added_deposit;
        assert(channels[key].deposit >= _added_deposit);
        emit ChannelToppedUp(_sender_address, _receiver_address, channels[key].open_block_number, _added_deposit);
    }

    /// @dev Deletes the channel and settles by transfering the balance to the receiver
    /// and the rest of the deposit back to the sender.
    /// @param _sender_address The address of the sender.
    /// @param _receiver_address The address of the receiver.
    /// @param _open_block_number The block number at which the channel was created.
    /// @param _balance The amount of tokens owed by the sender to the receiver.
    function settleChannel(
        address _sender_address,
        address _receiver_address,
        uint32 _open_block_number,
        uint256 _balance)
        private
    {
        bytes32 key = getKey(_sender_address, _receiver_address, _open_block_number);
        Channel memory channel = channels[key];

        require(channel.open_block_number > 0);
        require(_balance <= channel.deposit);
        require(withdrawn_balances[key] <= _balance);

        // Remove closed channel structures
        // Change state before transfer call
        delete channels[key];
        delete closing_requests[key];

        // Send the unwithdrawn _balance to the receiver
        uint256 _receiver_remaining_balance = _balance - withdrawn_balances[key];
        _receiver_address.transfer(_receiver_remaining_balance);

        // Send deposit - balance back to sender
        _sender_address.transfer(channel.deposit - _balance);

        emit ChannelSettled(
            _sender_address,
            _receiver_address,
            channel.open_block_number,
            _balance,
            _receiver_remaining_balance
        );
    }

    /*
     *  Internal functions
     */

    /// @dev Internal function to determine if an address is a contract
    /// @param _addr The address being queried
    /// @return True if `_addr` is a contract
    function isContract(address _addr) internal view returns (bool) {
        uint size;
        if (_addr == 0) return false;
        assembly {
            size := extcodesize(_addr)
        }
        return size>0;
    }
}
