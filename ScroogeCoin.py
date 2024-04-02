import hashlib
import json
from fastecdsa import ecdsa, keys, curve, point

class ScroogeCoin(object):
    def __init__(self):
        self.private_key, self.public_key = keys.gen_keypair(curve.secp256k1)
        self.address = int(hashlib.sha256(hex(self.public_key.x).encode()).hexdigest(), 16) << 2
        self.chain = [] # list of all blocks in blockchain
        self.current_transactions = [] # list of all the current transactions

    def create_coins(self, receivers: dict):
        """
        Scrooge adds value to some coins
        :param receivers: {account:amount, account:amount, ...}
        """

        tx = { # transaction
            "sender" : self.address,
            # coins that are created do not come from anywhere
            "locations": {"block": -1, "tx": -1, "amount":-1},
            "receivers" : receivers,
        }
        
        tx["hash"] = self.hash(tx)
        tx["signature"] = self.sign(tx["hash"])

        self.current_transactions.append(tx)

    def hash(self, blob):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        """
        # sort keys to get dictionary in order
        return hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest()

    def sign(self, hash_):
        return ecdsa.sign(hash_, self.private_key, curve.secp256k1)

    def get_user_tx_positions(self, address): # already created by professor!
        """
        Scrooge adds value to some coins
        :param address: User.address
        :return: list of all transactions where address is funded
        [{"block":block_num, "tx":tx_num, "amount":amount}, ...]
        """
        funded_transactions = []

        for block in self.chain:
            tx_index = 0
            for old_tx in block["transactions"]:
                for funded, amount in old_tx["receivers"].items():
                    if(address == funded):
                        funded_transactions.append({"block":block["index"], "tx":tx_index, "amount":amount})
                tx_index += 1

        return funded_transactions
    
    def hashHelper(self, tx, is_correct_hash):
        # The transaction is hashed correctly, so recreate making and hashing a transaction and comparing
        sender = tx["sender"]
        locations = tx["locations"]
        receivers = tx["receivers"]
        
        # from the User create transaction function
        newTx = {
                "sender" : sender,
                "locations" : locations,
                "receivers" : receivers
            }
        
        compareHash = self.hash(newTx)
        if compareHash == tx["hash"]:
            is_correct_hash == True
        else:
            print("Hash is incorrect!")
    

    def validate_tx(self, tx, public_key):
        """
        validates a single transaction

        Each transaction has a sender, receivers (which include the sender), and locations of previous transactions
        which all have sender, recevier, and previous transactions --> original Scrooge tx creation
        
        :param tx = {
            "sender" : User.address,
                ## a list of locations of previous transactions
                ## look at
            "locations" : [{"block":block_num, "tx":tx_num, "amount":amount}, ...],
            "receivers" : {account:amount, account:amount, ...}
        }
        
        Each block has a previous pointer, an index in the blockchain, and transactions it holds
        :param block = {
            'previous_hash': prevHash,
            'index': len(self.chain),
            'transactions': self.current_transactions, # might be empty but that's OK
        }

        :param public_key: User.public_key

        :return: if tx is valid return tx
        """
        is_correct_hash = False
        is_signed = False
        is_funded = False
        is_all_spent = False
        consumed_previous = False
        
        maxBlockChainIndex = len(self.chain)
        
        # See if hash is correct by hashing tx and then comparing to original hash for tx
        compareHash = self.hash({
                "sender" : tx["sender"],
                "locations" : tx["locations"],
                "receivers" : tx["receivers"]
            })
        
        if compareHash == tx["hash"]:
            is_correct_hash = True
        else:
            print("Hash is not correct!")
        
        # The consumed coins are valid, that is the coins are created in previous transactions
        for location in tx["locations"]:
            if location["block"] < maxBlockChainIndex: # in the blockchain check
                if location["tx"] < len(self.chain[location["block"]]["transactions"]): # number is in the correct block check
                    is_funded = True
                else: 
                    print("Consumed coins not funded!")
                    break
            else: 
                print("Consumed coins not funded!")
                break
        
        # The consumed coins were not already consumed in some previous
        # transaction. That is, this is not a double‐spend 
        # (basically trying to see if the tx is already in the blockchain)
        for location in tx["locations"]:
            i = location["block"]
            for block in self.chain[i:]: # have to look through the block to get the transactions
                for curtx in block["transactions"]:
                    if curtx["sender"] != tx["sender"]: # sender is the right sender check
                        continue  # skip
                    for curTxLocation in curtx["locations"]:
                        if curTxLocation["block"] == location["block"]:
                            if curTxLocation["tx"] == location["tx"]: 
                                print("Coins were already spent!")
                                consumed_previous = True

        # The total value of the coins that come out of this transaction is equal to
        # the total value of the coins that went in. That is, only Scrooge can create new value.
        input = output = 0

        for location in tx["locations"]:
            input += location["amount"]        
        for amount in tx["receivers"].values():
            output += amount
        if input < output:
            print("Too many coins going out!")
        elif input > output:
            print("Too many coins going in!")
        else: 
            is_all_spent = True

        # The transaction is validly signed by the owner of all the consumed coins
        if ecdsa.verify(tx["signature"], tx["hash"], public_key, curve.secp256k1) == True:
           is_signed = True
        else:
            print("Signature is not valid!")
        
        if (is_correct_hash and is_signed and is_funded and is_all_spent and not consumed_previous):
            return True
        else:
            return False


    def mine(self):
        """
        mines a new block onto the chain
        """
        if len(self.chain) > 0:
            prevHash = self.chain[-1] # get the last block in the chain if the chain has a block
        else: 
            prevHash = 0

        block = {
            'previous_hash': self.hash(prevHash),
            'index': len(self.chain),
            'transactions': self.current_transactions, # might be empty if transactions already consumed
        }
        
        # hash and sign the block
        block["hash"] = self.hash(block)
        block["signature"] = self.sign(block["hash"])
        
        # clear current transactions and add result to blockchain
        self.current_transactions = [] 
        self.chain.append(block)
        return block

    def add_tx(self, tx, public_key):
        """
        adds tx to current_transactions
        """
        
        # check to see if transaction is valid first
        if(self.validate_tx(tx, public_key) == False):
            return False

        self.current_transactions.append(tx)
        return True

    def show_user_balance(self, address):
        """
        prints balance of address
        :param address: User.address
        """
        # Compute the total balance of a user address.
        # You can scan all the chain to compute all the balance. Display the amount on the terminal.
        balance = 0
        
        # inspired from get_user_tx_positions
        for block in self.chain:
            for curtx in block["transactions"]:
                for account, amount in curtx["receivers"].items():
                    if address == account:
                        balance += amount
                    if address == curtx["sender"]:
                        balance -= amount
                
        print("User: ", address, "\t Balance: ", balance)

    def show_block(self, block_num):
        """
        prints out a single formated block
        :param block_num: index of the block to be printed
        """
        # Display the contents of a block for a given block number. In the header, 
        # you may display block number, previous
        # hash, and signature. Later, you can list all the transactions with
        # transaction number, sender, hash, location(location of the coins
        # consumed), receiver and signature information.
        
        for block in self.chain:
            if block["index"] == block_num: # ladies and gentlemen, we found our block!
                print("--- Block Number", block_num, " -------------------------------" )
                print("Previous Hash: ", block["previous_hash"])
                print("Hash: ", block["hash"])
                print("Signature: ", block["signature"])
                print()
                
                index = 1
                for curtx in block["transactions"]:
                    print("~~~ Transaction Number", index, " ~~~~~~~~~~~~~~~~~~~~~~~~~~" )
                    print("Sender: ", curtx["sender"])
                    print("Locations: ", curtx["locations"])
                    print("Receivers: ", curtx["receivers"])
                    print("Hash: ", curtx["hash"])
                    print("Signature: ", curtx["signature"])
                    print()
                    index += 1
        

class User(object):
    def __init__(self, Scrooge):
        self.private_key, self.public_key = keys.gen_keypair(curve.secp256k1)
        self.address = int(hashlib.sha256(hex(self.public_key.x).encode()).hexdigest(), 16) << 2 

    def hash(self, blob):
        """
        Creates a SHA-256 hash of a Block
        :param block: Block
        :return: the hash of the blob
        """
        return hashlib.sha256(json.dumps(blob, sort_keys=True).encode()).hexdigest()

    def sign(self, hash_):
        return ecdsa.sign(hash_, self.private_key, curve.secp256k1)

    def send_tx(self, receivers, previous_tx_locations):
        """
        creates a TX to be sent
        :param receivers: {account:amount, account:amount, ...}
        :param previous_tx_locations 
        """

        tx = {
                "sender" : self.address,
                "locations" : previous_tx_locations,
                "receivers" : receivers
            }

        tx["hash"] = self.hash(tx)
        tx["signature"] = self.sign(tx["hash"])

        return tx

def main():

    # dict - defined using {key:value, key:value, ...} or dict[key] = value
        # they are used in this code for blocks, transactions, and receivers
        # can be interated through using dict.items()
        # https://docs.python.org/3/tutorial/datastructures.html#dictionaries

    # lists -defined using [item, item, item] or list.append(item) as well as other ways
        # used to hold lists of blocks aka the blockchain
        # https://docs.python.org/3/tutorial/datastructures.html#more-on-lists

    # fastecdsa - https://pypi.org/project/fastecdsa/
    # hashlib - https://docs.python.org/3/library/hashlib.html
    # json - https://docs.python.org/3/library/json.html

    # From professor's code
    Scrooge = ScroogeCoin()
    users = [User(Scrooge) for i in range(10)]
    Scrooge.create_coins({users[0].address:10, users[1].address:20, users[3].address:50})
    
    # Testing
    print("~~~~ SETUP TESTING ~~~~")
    print("~ Initial Balance")
    Scrooge.show_user_balance(users[4].address)
    Scrooge.show_user_balance(users[5].address)
    Scrooge.show_user_balance(users[6].address)
    Scrooge.show_user_balance(users[7].address)
    Scrooge.show_user_balance(users[8].address)
    Scrooge.show_user_balance(users[9].address)
    Scrooge.create_coins({users[4].address:10, users[5].address:20, users[6].address:0})
    Scrooge.create_coins({users[7].address:10, users[8].address:20, users[9].address:0})
    Scrooge.mine()
    
    print("~ After Coin Creation and Mining")
    Scrooge.show_user_balance(users[4].address)
    Scrooge.show_user_balance(users[5].address)
    Scrooge.show_user_balance(users[6].address)
    Scrooge.show_user_balance(users[7].address)
    Scrooge.show_user_balance(users[8].address)
    Scrooge.show_user_balance(users[9].address)
    print()
    
    print("~~~~ SENDING COINS CORRECTLY TESTING ~~~~")    
    print("~ User 4 sends [8 COINS] to User 5, receiving [2 COINS] back")
    print("~~ Before transfer of [8 COINS] to User 5")
    sender = users[4]
    receiver = users[5]
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    
    firstTx = sender.send_tx({receiver.address:8, sender.address:2}, Scrooge.get_user_tx_positions(sender.address))
    Scrooge.add_tx(firstTx, sender.public_key)
    Scrooge.mine()
    
    print("~~ After transfer of [8 COINS] to User 5")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    print()
    
    print("~ User 5 sends [8 COINS] to User 4, receiving [20 COINS] back")
    sender = users[5]
    receiver = users[4]
    
    print("~~ Before transfer of [8 COINS] to User 4")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    
    secondTx = sender.send_tx({receiver.address:8, sender.address:20}, Scrooge.get_user_tx_positions(sender.address))
    Scrooge.add_tx(secondTx, sender.public_key)
    Scrooge.mine()
    
    print("~~ After transfer of [8 COINS] to User 4")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    print()
    
    print("~~~~ SENDING COINS INCORRECTLY TESTING ~~~~")
    
    print("~ Incorrect Signature")
    print("~~ User 7 Sends User 8 Coins While Using the Wrong Signature")
    sender = users[7]
    receiver = users[8]
    
    print("~~~ Before User 7 sends [5 COINS] to User 8")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    
    badSignatureTx = sender.send_tx({receiver.address:5, sender.address:5}, Scrooge.get_user_tx_positions(sender.address))
    # should be using the sender key but using receiver key instead
    Scrooge.add_tx(badSignatureTx, receiver.public_key) 
    Scrooge.mine()
    
    print("~~~ After User 7 sends [5 COINS] to User 8 (Failed)")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    print()
       
    
    print("~ Incorrect Funding")
    print("~~ User 4 Sends User 5 Coins That Don't Exist")
    sender = users[4]
    receiver = users[5]
    
    print("~~~ Before User 4 sends [5 NONEXISTENT COINS] to User 5")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    
    fakeTx = [{'block': 0, 'tx': 7, 'amount': 10}]
    nonexistentCoinsTx = sender.send_tx({receiver.address:5, sender.address:5}, fakeTx)
    Scrooge.add_tx(nonexistentCoinsTx, sender.public_key)
    Scrooge.mine()
    
    print("~~~ After User 4 sends [5 NONEXISTENT COINS] to User 5 (Failed)")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    print()
    
    print("~ Spending Too Many Coins ")
    print("~~ User Doesn't Have Enough Coins to Spend")
    sender = users[6] # user 6 has 0 coins
    receiver = users[4]
    
    print("~~~ Before User 6 sends [5 COINS] to User 4")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    
    notEnoughTx = sender.send_tx({receiver.address:5, sender.address:0}, Scrooge.get_user_tx_positions(sender.address))
    Scrooge.add_tx(notEnoughTx, sender.public_key)
    Scrooge.mine()
    
    print("~~~ After User 6 sends [5 COINS] to User 4 (Failed)")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    print()
    
    print("~~ Incorrect Number of Coins in the Transaction")
    sender = users[7]
    receiver = users[8]
    print("~~~ Before transfer of [7 COINS] to User 8 with No Received Coins Back")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    
    wrongNumberTx = sender.send_tx({receiver.address:7, sender.address:0}, Scrooge.get_user_tx_positions(sender.address))
    Scrooge.add_tx(wrongNumberTx, sender.public_key)
    Scrooge.mine()
    
    print("~~~ After transfer of [7 COINS] to User 8 (Failed)")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    print()
    
    print("~ Double Spending")
    print("~~ Spending Coins Already Spent in Another Transaction")
    sender = users[4]
    receiver = users[5]
    
    print("~~~ Before User 4 transfer of [5 SPENT COINS] to User 5")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)

    spentTx = sender.send_tx({receiver.address:5, sender.address:15}, Scrooge.get_user_tx_positions(sender.address))
    Scrooge.add_tx(spentTx, sender.public_key)
    Scrooge.mine()
    
    print("~~~ After User 4 transfer of [5 SPENT COINS] to User 5 (Failed)")
    Scrooge.show_user_balance(sender.address)
    Scrooge.show_user_balance(receiver.address)
    print()
    
    print("~~~~ PRINTING OUT INFORMATION TESTING ~~~~")
    Scrooge.show_block(1)

if __name__ == '__main__':
   main()
