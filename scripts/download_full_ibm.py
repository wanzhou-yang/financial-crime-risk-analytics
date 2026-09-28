"""Download the IBM AML-Data HI-Small transaction CSV from its Kaggle distribution."""
from pathlib import Path
from urllib.request import Request, urlopen
import os

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'data' / 'HI-Small_Trans.csv'
URL = ('https://www.kaggle.com/api/v1/datasets/download/'
       'ealtman2019/ibm-transactions-for-anti-money-laundering-aml'
       '?fileName=HI-Small_Trans.csv')


def main():
    if DEST.exists():
        print(f'Already present: {DEST} ({DEST.stat().st_size:,} bytes)')
        return
    temp = DEST.with_suffix('.csv.part')
    request = Request(URL, headers={'User-Agent': 'TransactionRiskExplorer/1.0'})
    try:
        with urlopen(request, timeout=120) as response, temp.open('wb') as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        if temp.stat().st_size < 100_000_000:
            raise ValueError('The download is unexpectedly small; leaving the partial file for inspection.')
        os.replace(temp, DEST)
        print(f'Downloaded {DEST} ({DEST.stat().st_size:,} bytes)')
    except Exception:
        if temp.exists():
            temp.unlink()
        raise


if __name__ == '__main__':
    main()
