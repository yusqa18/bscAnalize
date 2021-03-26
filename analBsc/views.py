from django.shortcuts import render

from datetime import datetime
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

import io
import base64, urllib


def stampToTime(timestamp: str):
    tsint = int(timestamp)
    return datetime.utcfromtimestamp(tsint).strftime('%Y-%m-%d')


def BoughtSoldGraph(bought, sold, ylabel):
    matplotlib.use('Agg')
    plt.figure(figsize=(20, 10))
    buf = io.BytesIO()
    dfBought = pd.DataFrame.from_dict(bought, orient='columns').groupby('timeStamp').sum()
    dfSold = pd.DataFrame.from_dict(sold, orient='columns').groupby('timeStamp').sum()
    ax = dfBought.plot(figsize=(20, 5))
    dfSold.plot(ax=ax)
    plt.ylabel(ylabel)
    plt.xlabel("Дата")

    plt.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    return urllib.parse.quote(string)


def GruopByPerson(data, PersonColumn: str):
    return pd.DataFrame \
        .from_dict(data, orient='columns') \
        .groupby(PersonColumn) \
        .sum() \
        .sort_values("value", ascending=False) \
        .to_dict('index')


def joinDf(data1, data2):
    # Страемся Группировать, но как-то нихуя не получается, но мы пробьеюмся(нет)
    df1 = pd.DataFrame.from_dict(data1, orient='columns').set_index('person').groupby('person').sum()
    df2 = pd.DataFrame.from_dict(data2, orient='columns').set_index('person').groupby('person').sum()
    JoinedDf = df1.join(df2, on='person', how='outer', lsuffix='_buy (BUSD)', rsuffix='_sold (BUSD)')
    JoinedDf.reset_index(drop=True, inplace=True)

    DfxBalance = []
    StDfxBalance = []
    LpDfxBalance = []
    for i in JoinedDf.to_dict('records'):
        RespondDfxBalance = requests.get(
            "https://api.bscscan.com/api?module=account"
            "&action=tokenbalance"
            "&contractaddress=0x74b3abb94e9e1ecc25bd77d6872949b4a9b2aacf"
            f"&address={i['person']}"
            "&tag=latest&apikey=YourApiKeyToken")
        resIntDfxBalance = int(RespondDfxBalance.json()["result"])
        DfxBalance.append(resIntDfxBalance / 10 ** 18)

        RespondStDfxBalance = requests.get(
            "https://api.bscscan.com/api?module=account"
            "&action=tokenbalance"
            "&contractaddress=0x11340dC94E32310FA07CF9ae4cd8924c3cD483fe"
            f"&address={i['person']}"
            "&tag=latest&apikey=YourApiKeyToken")
        resIntStDfxBalance = int(RespondStDfxBalance.json()["result"])
        StDfxBalance.append(resIntStDfxBalance / 10 ** 18)

        RespondLpDfxBalance = requests.get(
            "https://api.bscscan.com/api?module=account"
            "&action=tokenbalance"
            "&contractaddress=0xe7ff9aceb3767b4514d403d1486b5d7f1b787989"
            f"&address={i['person']}"
            "&tag=latest&apikey=YourApiKeyToken")
        resIntLpDfxBalance = int(RespondLpDfxBalance.json()["result"])
        LpDfxBalance.append(resIntLpDfxBalance / 10 ** 18)
        print(i['person'])

    JoinedDf['DfxBalance'] = DfxBalance
    JoinedDf['StDfxBalance'] = StDfxBalance
    JoinedDf['LpDfxBalance'] = LpDfxBalance


    return JoinedDf.to_html()


def SoldGraph(sold):
    plt.figure(figsize=(20, 10))
    matplotlib.use('Agg')
    buf = io.BytesIO()
    dfSold = pd.DataFrame.from_dict(sold, orient='columns').groupby('timeStamp').sum()
    dfSold.plot(figsize=(20, 5), color='green')
    plt.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    return urllib.parse.quote(string)


def dfGeneratorTodict(dfSoldPerson):
    returndict = []
    for person in dfSoldPerson:
        print(person)
        returndict.append({'address': person[0], 'value': person[1]})

    print(returndict[0])
    return returndict


# Create your views here.
def index(request):
    RespondSwap = requests.get(
        "https://api.bscscan.com/api?"
        "module=account"
        "&action=tokentx"
        "&address=0xe7ff9aceb3767b4514d403d1486b5d7f1b787989"
        "&startblock=0"
        "&endblock=25000000"
        "&sort=asc"
        "&apikey=YourApiKeyToken")
    resJsonSwap = RespondSwap.json()["result"]
    sold = []
    bought = []
    BusdSold = 0
    BusdBought = 0
    for transaction in resJsonSwap:
        transaction["timeStamp"] = stampToTime(transaction["timeStamp"])
        transaction["value"] = (int(transaction["value"])) / 10 ** (18)
        if transaction["tokenSymbol"] == "BUSD":
            if transaction["to"] == "0xe7ff9aceb3767b4514d403d1486b5d7f1b787989":
                bought.append({
                    "timeStamp": transaction["timeStamp"],
                    "value": transaction["value"],
                    "person": transaction["from"]
                })
                BusdBought += transaction["value"]
            elif transaction["from"] == "0xe7ff9aceb3767b4514d403d1486b5d7f1b787989":
                sold.append({
                    "timeStamp": transaction["timeStamp"],
                    "value": transaction["value"],
                    "person": transaction["to"]
                })
                BusdSold += transaction["value"]
    # Top buyer and seller
    dfBoughtPerson = GruopByPerson(bought, 'person')
    dfSoldPerson = GruopByPerson(sold, 'person')

    RespondStaking = requests.get(
        "https://api.bscscan.com/api"
        "?module=account&action=tokentx"
        "&address=0x11340dC94E32310FA07CF9ae4cd8924c3cD483fe"
        "&startblock=0"
        "&endblock=25000000"
        "&sort=asc"
        "&apikey=YourApiKeyToken")

    resJsonStaking = RespondStaking.json()["result"]

    stack = []
    merge = []
    ToStack = 0
    FromStack = 0

    for transaction in resJsonStaking:
        transaction["timeStamp"] = stampToTime(transaction["timeStamp"])
        transaction["value"] = (int(transaction["value"])) / 10 ** (18)
        if transaction["to"] == "0x11340dc94e32310fa07cf9ae4cd8924c3cd483fe":
            stack.append({
                "timeStamp": transaction["timeStamp"],
                "value": transaction["value"],
                "person": transaction["from"]
            })
            ToStack += transaction["value"]
        elif transaction["from"] == "0x11340dc94e32310fa07cf9ae4cd8924c3cd483fe":
            merge.append({
                "timeStamp": transaction["timeStamp"],
                "value": transaction["value"],
                "person": transaction["to"]
            })
            FromStack += transaction["value"]

    dfStack = GruopByPerson(stack, 'person')
    dfMerge = GruopByPerson(merge, 'person')

    return render(request, 'index.html', {
        "Df": joinDf(bought, sold),
        'BoughtGraph': BoughtSoldGraph(bought, sold, "Кол-во денях в BUSD"),
        'StackGraph': BoughtSoldGraph(stack, merge, "Кол-во токенов в DFX"),
        'dfBoughtPerson': dfBoughtPerson,
        'dfSoldPerson': dfSoldPerson,
        'dfStack': dfStack,
        'dfMerge': dfMerge,

    })


def home(request):
    plt.plot(range(10))
    fig = plt.gcf()
    # convert graph into dtring buffer and then we convert 64 bit code into image
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    string = base64.b64encode(buf.read())
    uri = urllib.parse.quote(string)
    return render(request, 'index.html', {'data': uri})
