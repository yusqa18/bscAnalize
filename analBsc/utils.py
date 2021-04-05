from datetime import datetime, timedelta
import pandas as pd
import requests
from web3 import Web3
from django.db.models import QuerySet

from .abi import abiDfx, abiStDfx, abiFarming, abiCakeLp

WEI = 10 ** 18
ST_DFX_ADDRESS = "0x11340dc94e32310fa07cf9ae4cd8924c3cd483fe"
DFX_ADDRESS = "0x74b3abb94e9e1ecc25bd77d6872949b4a9b2aacf"
FARMING_DFX_ADDRESS = "0x9d943fd36add58c42568ea1459411b291ff7035f"
CAKE_LP_ADDRESS = "0xe7ff9aceb3767b4514d403d1486b5d7f1b787989"


def get_res_Int_user_Balance_Of_Token__Balance(contract, address: str):
    resIntBalance = contract.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    return float(resIntBalance / WEI)


def get_res_Int_user_balance_farming_Dfx(contract, address: str):
    resIntBalance = contract.functions.userInfo(1, Web3.toChecksumAddress(address)).call()
    return float(resIntBalance[0] / WEI)


def stampToTime(timestamp: str):
    tsint = int(timestamp)
    return datetime.utcfromtimestamp(tsint).strftime('%Y-%m-%d')


def group_dataframe(data, sort_column):
    return pd.DataFrame.from_dict(data, orient='columns').groupby(sort_column).sum()


def parse_contract_transations(account_address: str, token_symbol):
    RespondSwap = requests.get(
        "https://api.bscscan.com/api?"
        "module=account"
        "&action=tokentx"
        f"&address={account_address}"
        "&startblock=0"
        "&endblock=25000000"
        "&sort=asc"
        "&apikey=YourApiKeyToken")
    resJsonSwap = RespondSwap.json()["result"]

    ToUs = []
    FromUs = []

    for transaction in resJsonSwap:

        if (transaction["tokenSymbol"] == token_symbol) or (token_symbol == ""):
            transaction["timeStamp"] = stampToTime(transaction["timeStamp"])
            transaction["value"] = (int(transaction["value"])) / WEI
            if transaction["to"] == account_address:
                ToUs.append({
                    "timeStamp": transaction["timeStamp"],
                    "value": transaction["value"],
                    "person": transaction["from"],
                    "hash": transaction["hash"]
                })
            elif transaction["from"] == account_address:
                FromUs.append({
                    "timeStamp": transaction["timeStamp"],
                    "value": transaction["value"],
                    "person": transaction["to"],
                    "hash": transaction["hash"]
                })
    return ToUs, FromUs


def group_4data_by_person(data1, data2, stackdata, mergedata):
    pd.set_option('display.float_format', lambda x: '%.5f' % x)
    w3 = Web3(Web3.HTTPProvider('https://bsc-dataseed1.binance.org:443'))
    df1 = group_dataframe(data1, 'person')
    df2 = group_dataframe(data2, 'person')
    dfStack = group_dataframe(stackdata, 'person')
    dfMerge = group_dataframe(mergedata, 'person')
    JoinedDf = df1.join(
        df2,
        on='person',
        how='outer',
        lsuffix='_buy (DFX)',
        rsuffix='_sold (DFX)')
    JoinedDf = JoinedDf.join(
        dfStack,
        on='person',
        how='outer',
        lsuffix='_ToStack (DFX)',
        rsuffix='Second')
    JoinedDf = JoinedDf.join(
        dfMerge,
        on='person',
        how='outer',
        lsuffix='_FromStack (DFX)',
        rsuffix='_ToStack (DFX)')
    JoinedDf.reset_index(drop=True, inplace=True)

    ContractDfx = w3.eth.contract(address=Web3.toChecksumAddress(DFX_ADDRESS), abi=abiDfx())
    ContractStDfx = w3.eth.contract(address=Web3.toChecksumAddress(ST_DFX_ADDRESS), abi=abiStDfx())
    ContractFarmingDfx = w3.eth.contract(address=Web3.toChecksumAddress(FARMING_DFX_ADDRESS), abi=abiFarming())
    ContractCekeLpToken = w3.eth.contract(address=Web3.toChecksumAddress(CAKE_LP_ADDRESS), abi=abiCakeLp())

    DFX_BALANCE_OF_STDFX_ON_DFX = float(
        ContractDfx.functions.balanceOf(
            Web3.toChecksumAddress(ST_DFX_ADDRESS)
        ).call() / WEI)
    DFX_BALANCE_OF_CAKE_LP_ON_DFX = float(
        ContractDfx.functions.balanceOf(
            Web3.toChecksumAddress(CAKE_LP_ADDRESS)
        ).call() / WEI)

    STDFX_TOTAL_SUPLY = float(ContractStDfx.functions.totalSupply().call() / WEI)
    CAKE_LP_TOTAL_SUPLY = float(ContractCekeLpToken.functions.totalSupply().call() / WEI)

    DfxBalance = []
    StDfxBalance = []
    LpFarmingBalance = []
    UserDfxAmountFromStDFX = []
    UserDfxAmountFromCakeLP = []
    SumOfDfxOfUser = []
    print('start get add info')
    for i in JoinedDf.to_dict('records'):
        print(type(i['person']))
        DfxBalanceUser = get_res_Int_user_Balance_Of_Token__Balance(ContractDfx, i['person'])
        DfxBalance.append(DfxBalanceUser)

        StDfxBalanceOfPerson = get_res_Int_user_Balance_Of_Token__Balance(ContractStDfx, i['person'])
        StDfxBalance.append(StDfxBalanceOfPerson)
        UserDfxAmountFromStDFX.append(StDfxBalanceOfPerson * DFX_BALANCE_OF_STDFX_ON_DFX / STDFX_TOTAL_SUPLY)

        CakeLpBalanceOfPerson = get_res_Int_user_balance_farming_Dfx(ContractFarmingDfx, i['person'])
        LpFarmingBalance.append(CakeLpBalanceOfPerson)
        UserDfxAmountFromCakeLP.append(CakeLpBalanceOfPerson * DFX_BALANCE_OF_CAKE_LP_ON_DFX / CAKE_LP_TOTAL_SUPLY)

        SumOfDfxOfUser.append(DfxBalanceUser + StDfxBalanceOfPerson + CakeLpBalanceOfPerson)
    print('stop get add info')
    JoinedDf['DfxBalance'] = DfxBalance
    JoinedDf['StDfxBalance'] = StDfxBalance
    JoinedDf['LpFarmingBalance'] = LpFarmingBalance
    JoinedDf['UserDfxAmountFromStDFX'] = UserDfxAmountFromStDFX
    JoinedDf['UserDfxAmountFromCakeLP'] = UserDfxAmountFromCakeLP
    JoinedDf['SumOfDfxOfUser'] = SumOfDfxOfUser
    return JoinedDf.fillna(0).to_dict('records')



def balance_of_persons(persons_query_set: QuerySet):
    w3 = Web3(Web3.HTTPProvider('https://bsc-dataseed1.binance.org:443'))
    ContractDfx = w3.eth.contract(address=Web3.toChecksumAddress(DFX_ADDRESS), abi=abiDfx())
    ContractStDfx = w3.eth.contract(address=Web3.toChecksumAddress(ST_DFX_ADDRESS), abi=abiStDfx())
    ContractFarmingDfx = w3.eth.contract(address=Web3.toChecksumAddress(FARMING_DFX_ADDRESS), abi=abiFarming())
    ContractCekeLpToken = w3.eth.contract(address=Web3.toChecksumAddress(CAKE_LP_ADDRESS), abi=abiCakeLp())
    DFX_BALANCE_OF_STDFX_ON_DFX = float(
        ContractDfx.functions.balanceOf(
            Web3.toChecksumAddress(ST_DFX_ADDRESS)
        ).call() / WEI)
    DFX_BALANCE_OF_CAKE_LP_ON_DFX = float(
        ContractDfx.functions.balanceOf(
            Web3.toChecksumAddress(CAKE_LP_ADDRESS)
        ).call() / WEI)
    STDFX_TOTAL_SUPLY = float(ContractStDfx.functions.totalSupply().call() / WEI)
    CAKE_LP_TOTAL_SUPLY = float(ContractCekeLpToken.functions.totalSupply().call() / WEI)

    SumOfDfxOfUser = []
    result = {}
    j = 0
    for i in persons_query_set:
        print(type(i.blockchain_address))
        DfxBalanceUser = get_res_Int_user_Balance_Of_Token__Balance(ContractDfx, i.blockchain_address)

        StDfxBalanceOfPerson = get_res_Int_user_Balance_Of_Token__Balance(ContractStDfx, i.blockchain_address)
        UserDfxAmountFromStDFX = StDfxBalanceOfPerson * DFX_BALANCE_OF_STDFX_ON_DFX / STDFX_TOTAL_SUPLY

        CakeLpBalanceOfPerson = get_res_Int_user_balance_farming_Dfx(ContractFarmingDfx, i.blockchain_address)
        UserDfxAmountFromCakeLP = CakeLpBalanceOfPerson * DFX_BALANCE_OF_CAKE_LP_ON_DFX / CAKE_LP_TOTAL_SUPLY

        SumOfDfxOfUser.append(DfxBalanceUser + UserDfxAmountFromStDFX + UserDfxAmountFromCakeLP)
        j += 1
        print(j)

    sumOfBalance = sum(SumOfDfxOfUser)
    for i in range(len(persons_query_set)):
        result[persons_query_set[i].blockchain_address] = SumOfDfxOfUser[i] / sumOfBalance

    return result, sumOfBalance


def user_Dfx_balance(address: str):
    w3 = Web3(Web3.HTTPProvider('https://bsc-dataseed1.binance.org:443'))
    ContractDfx = w3.eth.contract(address=Web3.toChecksumAddress(DFX_ADDRESS), abi=abiDfx())
    ContractStDfx = w3.eth.contract(address=Web3.toChecksumAddress(ST_DFX_ADDRESS), abi=abiStDfx())
    ContractFarmingDfx = w3.eth.contract(address=Web3.toChecksumAddress(FARMING_DFX_ADDRESS), abi=abiFarming())
    ContractCekeLpToken = w3.eth.contract(address=Web3.toChecksumAddress(CAKE_LP_ADDRESS), abi=abiCakeLp())
    DFX_BALANCE_OF_STDFX_ON_DFX = float(
        ContractDfx.functions.balanceOf(
            Web3.toChecksumAddress(ST_DFX_ADDRESS)
        ).call() / WEI)
    DFX_BALANCE_OF_CAKE_LP_ON_DFX = float(
        ContractDfx.functions.balanceOf(
            Web3.toChecksumAddress(CAKE_LP_ADDRESS)
        ).call() / WEI)
    STDFX_TOTAL_SUPLY = float(ContractStDfx.functions.totalSupply().call() / WEI)
    CAKE_LP_TOTAL_SUPLY = float(ContractCekeLpToken.functions.totalSupply().call() / WEI)

    print(type(address))
    resIntDfxBalance = ContractDfx.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    DfxBalanceUser = float(resIntDfxBalance / WEI)

    resIntStDfxBalance = ContractStDfx.functions.balanceOf(Web3.toChecksumAddress(address)).call()
    StDfxBalanceOfPerson = float(resIntStDfxBalance / WEI)
    UserDfxAmountFromStDFX = StDfxBalanceOfPerson * DFX_BALANCE_OF_STDFX_ON_DFX / STDFX_TOTAL_SUPLY

    resIntFarmingDfxBalance = ContractFarmingDfx.functions.userInfo(1, Web3.toChecksumAddress(address)).call()
    CakeLpBalanceOfPerson = float(resIntFarmingDfxBalance[0] / WEI)
    UserDfxAmountFromCakeLP = CakeLpBalanceOfPerson * DFX_BALANCE_OF_CAKE_LP_ON_DFX / CAKE_LP_TOTAL_SUPLY

    SumOfDfxOfUser = DfxBalanceUser + UserDfxAmountFromStDFX + UserDfxAmountFromCakeLP
    return SumOfDfxOfUser


def group_by_time(to_data, from_data):
    toDataGroped = pd.DataFrame.from_dict(to_data, orient='columns').groupby('timeStamp').sum()
    fromDataGroped = pd.DataFrame.from_dict(from_data, orient='columns').groupby('timeStamp').sum()
    joinedDf = toDataGroped.join(
        fromDataGroped,
        how='outer',
        lsuffix='_Stack',
        rsuffix='_Merge'
    ).fillna(0).to_dict('index')

    return joinedDf


def group_by_time_with_hash(to_data_dfx, from_data_dfx, to_data_busd, from_data_busd):
    toDataGropedDfx = pd.DataFrame.from_dict(to_data_dfx, orient='columns').set_index('hash')
    fromDataGropedDfx = pd.DataFrame.from_dict(from_data_dfx, orient='columns').set_index('hash')
    toDataGropedBusd = pd.DataFrame.from_dict(to_data_busd, orient='columns').set_index('hash')
    fromDataGropedBusd = pd.DataFrame.from_dict(from_data_busd, orient='columns').set_index('hash')

    JoinedDfSell = toDataGropedDfx.join(
        fromDataGropedBusd,
        on='hash',
        how='inner',
        lsuffix='DFX',
        rsuffix='Busd').groupby("timeStampDFX").sum()

    JoinedDfBought = fromDataGropedDfx.join(
        toDataGropedBusd,
        on='hash',
        how='inner',
        lsuffix='DFX',
        rsuffix='Busd').groupby("timeStampDFX").sum()

    Result = JoinedDfSell.join(
        JoinedDfBought,
        how='outer',
        lsuffix='Sell',
        rsuffix='Buy'
    ).fillna(0)

    return Result.to_dict('index')


def total_supply_request():
    RespondSwap = requests.get(
        "https://api.bscscan.com/api?"
        "module=stats&action=tokensupply"
        "&contractaddress=0x74b3abb94e9e1ecc25bd77d6872949b4a9b2aacf"
        "&apikey=X7UE235AN5BWK43SPCUPG2DZAQPZ9BPG46"
    )
    return RespondSwap.json()["result"]


def get_yesterday_delta(table):
    yesterday_time = (datetime.now() - timedelta(1)).strftime('%Y-%m-%d')
    yesterday_data = table[yesterday_time]
    print(yesterday_data)
    print(yesterday_time)
    result = yesterday_data["valueDFXBuy"] - yesterday_data["valueDFXSell"]
    return result
