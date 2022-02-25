# Python built-ins
from csv import reader
from typing import List
from datetime import datetime
import copy
# Require installation
import pandas as pd
from currency_converter import CurrencyConverter, ECB_URL  # https://pypi.org/project/CurrencyConverter/


class IsraeliTaxReport:
    """
    This class is intended to assist with filling out an Israeli annual tax report for Israelis 
    who own stocks in a US brokerage account from which taxes are not automatically paid upon sells of stocks 
    and therefore need to be reported. Currently, it can only handle a report from Interactive Brokers data, 
    but the class can quite easily be edited to handle other formats of raw data by editting its 'keywords' attribute.

    The main method, 'form1325', outputs the lines of form '1325', which is the main form used to report taxable trades 
    (and is not trivial to generate directly from the broker report). 
    
    The class has other useful attributes for the tax report, such as 'ustax_paid_df', 
    which contain the taxes paid in the us (usually due to dividends).

    Most of the attributes are Pandas dataframes. This class is not optimized for speed 
    but for ease of reading and submitting tax report data (typically done once or twice a year).

    See the README.md page for more details and how to provide a proper input .csv file.
    """
    # CLASS VARIABLES
    # key words in .csv (below for Interactive Broker report):
    keywords = {'trades': 'Trades',
                     'stocks': 'Stocks',
                  'dividends': 'Dividends',
                       'date': 'Date/Time',
                     'symbol': 'Symbol',
                   'quantity': 'Quantity',
                      'basis': 'Basis',
                 'asset type': 'Asset Category',
                  'data type': 'DataDiscriminator',
                'US tax paid': 'Withholding Tax',
                      'order': 'Order',
                'cash report': 'Cash Report',
                     'amount': 'Amount'}
    # columns dictionary of output form '1325' (for Israeli tax report)
    form1325dict = {'מספר': [],
                    'זיהוי מלא של נייר הערך שנמכר לפי הסדר הכרונולוגי של המכירות': [],
                    'נרכש טרם הרישום למסחר': [],
                    'Quantity': [], 
                    'ערך נקוב במכירה': [],
                    'תאריך הרכישה': [],
                    'Cost in USD': [],
                    'מחיר מקורי': [],
                    '1 + שיעור עליית המדד': [],
                    'מחיר מתואם': [],
                    'תאריך המכירה': [],
                    'תמורה': [],
                    'רווח הון ריאלי בשיעור מס של 25%': [],
                    'הפסד הון': []}
    # instantiate Currency Converter (https://pypi.org/project/CurrencyConverter/)
    converter = CurrencyConverter(ECB_URL, 
                                  fallback_on_missing_rate=True,
                                  fallback_on_missing_rate_method="last_known")
    # foreign currency symbol
    forex = 'USD'
    # native currency symbol
    base_currency = 'ILS'
    
    def __init__(self, csv_name=None):
        # input .csv file name. This is the file provided by the broker
        self.csv_name = csv_name
        # all trade rows in input .csv file
        trades = self.get_from_csv(csv_name=self.csv_name, 
                                   match=[self.keywords['trades']], 
                                   exclude=[])
        # data frame of all trades
        self.trades_df = pd.DataFrame(trades[1:], columns=trades[0])
        # data frame of all individual stock trades (buy or sell)
        self.stocks_df = self.trades_df.loc[
            (self.trades_df[self.keywords['asset type']] == self.keywords['stocks'])
            & (self.trades_df[self.keywords['data type']] == self.keywords['order'])]
        # data frame of all individual stock SELLS
        self.stock_sells_df = self.stocks_df.loc[
            self.trades_df[self.keywords['quantity']] < str(0)].sort_values(by=self.keywords['date'])
        # data frame of all individual stock BUYS
        self.stock_buys_df = self.stocks_df.loc[
            self.trades_df[self.keywords['quantity']] > str(0)].sort_values(by=self.keywords['date'])
        # all dividend rows in input .csv file
        dividends = self.get_from_csv(csv_name=self.csv_name,
                                      match=[self.keywords['dividends']], 
                                      exclude=[self.keywords['cash report']])
        # data frame of all individual dividend payments
        self.dividends_df = pd.DataFrame(dividends[1:], columns=dividends[0])
        # all US taxes paid in input .csv file
        ustax_paid = self.get_from_csv(csv_name=self.csv_name,
                                      match=[self.keywords['US tax paid']], 
                                      exclude=[self.keywords['cash report']])
        # data frame of all US tax deductions
        self.ustax_paid_df = pd.DataFrame(ustax_paid[1:], columns=ustax_paid[0])

    @staticmethod
    def get_from_csv(csv_name: str, match: List[str], exclude: List[str], match_all=False):
        """
        Returns all the lines from a .csv file (csv_name)
        that contain the words given in a list (match)
        and does not contain the words given in another list (exclude)

            Parameters:
                csv_name (str): name of the .csv file, e.g. 'file.csv'
                match (List[str]): words to match in line, e.g. ['cat', 'small']
                exclude (List[str]): words not to match in line, e.g. ['yellow'] or []
                match_all (bool): each line must match all words in 'match'? (default is False)

            Returns:
                List of sublists, each sublist is a line from the original .csv file
        """
        with open(csv_name, 'r') as read_obj:
            data = []
            csv_reader = reader(read_obj)
            for row in csv_reader:
                match_logic = any(word in row for word in match)
                exclude_logic = not any(word in row for word in exclude)
                # match all words in 'match' (match_all=True)
                if match_all:
                    if set(match).issubset(row) & exclude_logic:
                        data.append(row)
                # match any word in 'match' (match_all=False)
                elif match_logic & exclude_logic:
                    data.append(row)
        return data
        
    def apply_fifo(self, row_count, symbol: str, buys, sells, form_dict):
        for sell in sells.iterrows():
            # initialize number of stocks accounted for
            tot_quant_buys = 0
            # number of stocks sold in 'sell'
            quant_sell = abs(int(sell[1][self.keywords['quantity']]))
            while (tot_quant_buys < quant_sell) & (buys.shape[0] > 0):
                # row number in output form
                row_count += 1
                # currnet processed buy
                buy = buys.head(1)
                # quantity (number of stocks) of current buy
                quant_buy = int(buy[self.keywords['quantity']])
                # in case of partial sell of the buy
                if quant_buy > quant_sell - tot_quant_buys:
                    quant_buy = quant_sell - tot_quant_buys
                    partial = True
                else:
                    partial = False
                # generate row    
                row = [row_count, symbol].extend(self.calculate_row1325(buy, sell, quant_buy, quant_sell))  
                # add row to the form dictionary
                for key, val in zip(form_dict.keys(), row):
                    form_dict[key].append(val)
                # update or remove buy (already accounted for)
                if partial:
                    buys.iloc[0, :][self.keywords['quantity']] -= quant_buy
                else:
                    buys = buys.iloc[1:, :]
                # update number of stocks accounted for
                tot_quant_buys += quant_buy
        #print(form_dict)
        #return row_count, form_dict
        return form_dict
        
    def calculate_row1325(self, buy, sell, quant_buy: int, quant_sell: int, round_vals=True):
        """
        Calculates a row of the Israeli tax form '1325'
        
            Parameters:
                buy (dataframe): currnet processed buy
                sell (dataframe): sell of specific stock
                quant_buy (int): quantity (number of stocks) of current buy
                quant_sell (int): number of stocks sold in 'sell'

            Returns:
                A list correponding to the calculated row values of form '1325'
        """
        # pre-market hours? (empty in normal trading)
        pre_hrs = ''
        # sell total price for batch in USD
        sold_for_usd = (quant_buy / quant_sell) * abs(float(sell[1][self.keywords['basis']]))
        # date this batch was bought
        buy_date = buy[self.keywords['date']].values[0]
        buy_date = buy_date.split(',')[0]  # keep only date (with IB format)
        # date this batch was sold
        sell_date = sell[1][self.keywords['date']]
        sell_date = sell_date.split(',')[0]  # keep only date (with IB format)
        # conversion rate (1 USD in ILS) when bought
        rate_buy = self.converter.convert(1, self.forex, self.base_currency,
                                          datetime.strptime(buy_date, '%Y-%m-%d'))
        # conversion rate (1 USD in ILS) when sold
        rate_sell = self.converter.convert(1, self.forex, self.base_currency,
                                           datetime.strptime(sell_date, '%Y-%m-%d'))
        # cost in USD of batch
        cost_usd = (min(quant_buy, quant_sell) / quant_buy) * float(buy[self.keywords['basis']])
        # cost in ILS of batch
        cost_ils = rate_buy * cost_usd
        # relative change in conversion rate from sell to buy
        rate_change = rate_sell / rate_buy
        # cost in ILS adjusted for relative change in USD to ILS
        adj_cost_ils = cost_ils * rate_change
        # sell total price for batch in ILS
        sold_for_ils = sold_for_usd * rate_sell
        # if sell price in USD is greater than cost in USD, calculate 'real return'
        if sold_for_usd > cost_usd:
            real_return = max(min(sold_for_ils - adj_cost_ils, sold_for_ils - cost_ils), 0)
            real_loss = ''
        # if sell price in USD is smaller than cost in USD, calculate 'real loss'
        else:
            real_return = ''
            real_loss = min(max(sold_for_ils - adj_cost_ils, sold_for_ils - cost_ils), 0)
        # row to be added to form '1325'
        row = [pre_hrs, quant_buy, sold_for_usd, buy_date, cost_usd, cost_ils,
               rate_change, adj_cost_ils, sell_date, sold_for_ils, real_return, real_loss]
        # round number entries in row
        if round_vals:
            for i in range(len(row)):
                if type(row[i]) == float or type(row[i]) == int:
                    row[i] = round(row[i], 3)
        return row
        
    def form1325(self, year: str, save_as_csv=False):
        """
        Returns a Pandas dataframe corresponding to the Israeli tax form '1325'
        assumes that relevant data (buy & sell orders) is found in .csv used by class

            Parameters:
                year (str): the year to report in a 'yyyy' format, e.g. '2021'
                save_as_csv (bool): default is False

            Returns:
                Pandas dataframe with the with claculated return/loss
                according to the 'FIFO' (fist in first out) logic
        """
        # to be filled with rows of form '1325'
        form_dict = copy.deepcopy(self.form1325dict)
        row_count = 0
        # copies of all buy & sell orders
        all_buys = self.stock_buys_df.reset_index()
        all_sells = self.stock_sells_df.reset_index()
        # unique symbols of sold stocks, e.g. ['TSLA', 'VTI']
        symbols = all_sells[self.keywords['symbol']].unique()
        for symbol in symbols:
            # buys of specific stock 'symbol'
            buys = all_buys.loc[all_buys[self.keywords['symbol']] == symbol]
            # sells of specific stock 'symbol'
            sells = all_sells.loc[all_sells[self.keywords['symbol']] == symbol]
            
            form_dict = self.apply_fifo(row_count, symbol, buys, sells, form_dict)
                      
        form1325_df = pd.DataFrame(form_dict)
        # keep only sells in the tax year 'year'
        form1325_df = form1325_df.loc[(form1325_df['תאריך המכירה'] >= year + '-01-01') &
                                      (form1325_df['תאריך המכירה'] <= year + '-12-31')]
        # sort sell dates in ascending order
        form1325_df.sort_values(by='תאריך המכירה')
        # convert all dates from Y-m-d to Israeli format d-m-Y
        form1325_df['תאריך הרכישה'] = form1325_df['תאריך הרכישה'].str.split('-').str[::-1].str.join('-')
        form1325_df['תאריך המכירה'] = form1325_df['תאריך המכירה'].str.split('-').str[::-1].str.join('-')
        # save output form as .csv
        if save_as_csv:
            form1325_df[form1325_df.columns[::-1]].to_csv('form1325_' + year + '.csv',
                                                    index=False, encoding='utf-8-sig')
        return form1325_df
