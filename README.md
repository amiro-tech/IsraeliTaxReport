# The IsraeliTaxReport class
This class is intended to assist with filling out an Israeli annual tax report for Israelis who own stocks in a US brokerage account from which taxes are not automatically paid upon sells of stocks and therefore need to be reported. Currently, it can only handle a report from Interactive Brokers data. 
    
The main method, 'form1325', outputs the lines of form '1325', which is the main form used to report taxable trades and is not trivial to generate directly from the broker report. The class has other useful attributes for the tax report, such as 'ustax_paid_df', which contain the taxes paid in the us (usually due to dividends).

## Instruction for using the IsraeliTaxReport class

### [1] Obtain the raw report from Interactive Brokers as a .csv file:
* On your Interactive Brokers page, go to **Performance & Statements** and under **Reports**, choose **Statements**

![](imagesForREADME/image1.png)

* Create a **Custom Statement**

![](imagesForREADME/image2.png)

* Under **Sections**, choosing the following is currently sufficient:

![](imagesForREADME/image3.png)

* **Section Configurations** can be left as the default.
* **Delivery Configurations** - choose Format: CSV, Period: Daily, Language: English.
* Now you can run the statement, which is saved under **Custom Statements**.

### [2] To instantiate the IsraeliTaxReport class (in the same directory as IsraeliTaxReport.py):

```Python
from IsraeliTaxReport import IsraeliTaxReport

csv_name = 'custom_statement.csv'  # This is the custom statement generated in Interactive Brokers
report = IsraeliTaxReport(csv_name)
```

