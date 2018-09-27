from flask_restful import Resource, reqparse
import json
from collections import defaultdict

from microraiden.utils import sign_close
from eth_utils import encode_hex, is_address, to_checksum_address

from microraiden.channel_manager import Channel, ChannelManager
from microraiden.exceptions import NoOpenChannel, InvalidBalanceProof
from microraiden.exceptions import (
    NoBalanceProofReceived,
    InvalidBalanceProof,
)

class ChannelManagementRoot(Resource):
    @staticmethod
    def get():
        return "OK"


class ChannelManagementStats(Resource):
    def __init__(self, channel_manager: ChannelManager):
        super(ChannelManagementStats, self).__init__()
        self.channel_manager = channel_manager

    def get(self):
        deposit_sum = sum([c.deposit for c in self.channel_manager.channels.values()])
        unique_senders = {}
        open_channels = []
        pending_channels = []
        for k, v in self.channel_manager.channels.items():
            unique_senders[k[0]] = 1
            if v.is_closed is True:
                pending_channels.append(v)
            else:
                open_channels.append(v)
        contract_address = self.channel_manager.channel_manager_contract.address
        return {'balance_sum': self.channel_manager.get_locked_balance(),
                'deposit_sum': deposit_sum,
                'open_channels': len(open_channels),
                'pending_channels': len(pending_channels),
                'unique_senders': len(unique_senders),
                'liquid_balance': self.channel_manager.get_liquid_balance(),
                'contract_address': contract_address,
                'receiver_address': self.channel_manager.receiver,
                'manager_abi': self.channel_manager.channel_manager_contract.abi,
                'sync_block': self.channel_manager.blockchain.sync_start_block
                }


class ChannelManagementListChannels(Resource):
    def __init__(self, channel_manager: ChannelManager):
        super(ChannelManagementListChannels, self).__init__()
        self.channel_manager = channel_manager

    def get_all_channels(self, channel_status='all', condition=lambda k, v: True):
        return [v.to_dict() for k, v in self.channel_manager.channels.items()
                if (condition(k, v))]

    def get_channel_filter(self, channel_status='all'):
        if channel_status == 'open' or channel_status == 'opened':
            return lambda c: c.is_closed is False
        elif channel_status == 'closed':
            return lambda c: c.is_closed is True
        else:
            return lambda c: True

    def get(self, sender_address=None):
        parser = reqparse.RequestParser()
        parser.add_argument('status', type=str, help='filter channels by a status', default='all',
                            choices=('closed', 'opened', 'open', 'all'))
        args = parser.parse_args()
        channel_filter = self.get_channel_filter(args['status'])

        # if sender exists, return all open blocks
        if sender_address is not None and is_address(sender_address):
            ret = self.get_all_channels(
                condition=lambda k, v:
                (k[0] == to_checksum_address(sender_address) and
                 channel_filter(v))
            )

        # if sender is not specified, return all open channels
        else:
            ret = self.get_all_channels(condition=lambda k, v:
                                             channel_filter(v))
        return ret, 200

    def delete(self, sender_address):
        parser = reqparse.RequestParser()
        parser.add_argument('open_block', type=int, help='block the channel was opened')
        parser.add_argument('signature', help='last balance proof signature')
        args = parser.parse_args()
        if args.signature is None:
            return "Bad signature format", 400
        if args.block is None:
            return "No opening block specified", 400
        if sender_address and is_address(sender_address):
            sender_address = to_checksum_address(sender_address)
        channel = self.channel_manager.channels[sender_address, args.block]
        if channel.last_signature != args.signature:
            return "Invalid or outdated balance signature", 400
        ret = sign_close(self.channel_manager.private_key, args.signature)
        return ret, 200


class ChannelManagementChannelInfo(Resource):
    def __init__(self, channel_manager):
        super(ChannelManagementChannelInfo, self).__init__()
        self.channel_manager = channel_manager

    def get(self, sender_address, opening_block):
        if sender_address and is_address(sender_address):
            sender_address = to_checksum_address(sender_address)
        try:
            key = (sender_address, opening_block)
            sender_channel = self.channel_manager.channels[key]
        except KeyError:
            return "channel not found", 404

        return sender_channel.to_dict(), 200

    def delete(self, sender_address, opening_block):
        parser = reqparse.RequestParser()
        parser.add_argument('balance', type=int, help='last balance proof balance')
        args = parser.parse_args()
        if args.balance is None:
            return "Bad balance format", 400
        if sender_address and is_address(sender_address):
            sender_address = to_checksum_address(sender_address)

        try:
            close_signature = self.channel_manager.sign_close(
                sender_address,
                opening_block,
                args.balance)
        except (NoOpenChannel, InvalidBalanceProof) as e:
            return str(e), 400
        except KeyError:
            return "Channel not found", 404
        ret = {'close_signature': encode_hex(close_signature)}

        return ret, 200
