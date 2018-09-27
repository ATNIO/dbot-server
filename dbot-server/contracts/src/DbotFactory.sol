pragma solidity ^0.4.20;


contract StateChannel {
    function withdraw(uint32 _open_block_number, uint256 _balance, bytes _balance_msg_sig) external returns (uint256);
}


contract Ownable {

    address owner;

    event OwnershipTransferred(address previousOwner, address newOwner);

    constructor () public {
        owner = msg.sender;
    }

    modifier onlyOwner {
        if (msg.sender != owner)
            revert();
        _;
    }

    function transferOwnership(address _owner) onlyOwner public {
        require(_owner != address(0));
        emit OwnershipTransferred(owner, _owner);
        owner = _owner;
    }
}


contract Dbot is Ownable {

    struct Endpoint {
        bytes32 method;
        uint256 price;
        bytes32 uri;
    }

    address public sc = 0x0000000000000000000000000000000000000012;

    bytes32 public name;
    bytes32 public domain;
    mapping(bytes32 => Endpoint) public keyToEndPoints;

    event CreateDbot(bytes32 name, bytes32 domain, bytes32 method, uint256 price, bytes32 uri, bytes32 key);
    event ChangeName(bytes32 name);
    event ChangeDomain(bytes32 domain);
    event AddEndPoint(bytes32 method, uint256 price, bytes32 uri, bytes32 key);
    event UpdateEndPoint(bytes32 method, uint256 price, bytes32 uri, bytes32 key);
    event DeleteEndPoint(bytes32 method, bytes32 uri, bytes32 key);

    constructor (bytes32 _name, bytes32 _domain, bytes32 _method, uint256 _price, bytes32 _uri) public {
        require((_method != 0) && ( _uri != 0), 'method or uri cannot be null');
        name = _name;
        domain = _domain;
        bytes32 key = getKey(_method, _uri);
        keyToEndPoints[key] = Endpoint(_method, _price, _uri);
        emit CreateDbot(_name, _domain, _method, _price, _uri, key);
    }

    function withdrawFromChannel(uint256 _balance, bytes _balance_msg_sig) onlyOwner public {
        uint256 withdrawed = StateChannel(sc).withdraw(1, _balance, _balance_msg_sig);
        msg.sender.transfer(withdrawed);
    }

    function withdraw() onlyOwner public {
        msg.sender.transfer(address(this).balance);
    }

    function getOwner() public view returns (address) {
        return owner;
    }

    function getKey(bytes32 _method, bytes32 _uri) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(_method, _uri));
    }

    function changeName(bytes32 _name) onlyOwner public {
        name = _name;
        emit ChangeName(_name);
    }

    function changeDomain(bytes32 _domain) onlyOwner public {
        domain = _domain;
        emit ChangeDomain(_domain);
    }

    function addEndPoint(bytes32 _method, uint256 _price, bytes32 _uri) onlyOwner public {
        bytes32 key = getKey(_method, _uri);
        keyToEndPoints[key] = Endpoint(_method, _price, _uri);
        emit AddEndPoint(_method, _price, _uri, key);
    }

    function updateEndPoint(bytes32 _method, uint256 _price, bytes32 _uri) onlyOwner public {
        bytes32 key = getKey(_method, _uri);
        require((keyToEndPoints[key].method != 0) && (keyToEndPoints[key].uri != 0), "no key");
        keyToEndPoints[key].price = _price;
        emit UpdateEndPoint(_method, _price, _uri, key);
    }

    function deleteEndPoint(bytes32 _method, bytes32 _uri) onlyOwner public {
        bytes32 key = getKey(_method, _uri);
        delete keyToEndPoints[key];
        emit DeleteEndPoint(_method, _uri, key);
    }

    function() public payable {}

}

contract DbotFactory {

    address[] public dbots;

    event Register(uint256 id, address dbotAddress);

    mapping(uint256 => address) public idToAddress;

    function register(address _dbotAddress) public {
        uint256 _id = dbots.push(_dbotAddress) - 1;
        idToAddress[_id] = _dbotAddress;
        emit Register(_id, _dbotAddress);
    }

}
