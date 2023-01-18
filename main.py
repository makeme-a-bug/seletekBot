from reporter.manager import ReporterManager
import glob
import pandas as pd

if __name__ == "__main__":
    bot = ReporterManager()


def merge_reports(fold , fold2):
    files = []
    print(glob.glob(f"{fold}/*"))
    print(glob.glob(f"{fold2}/*"))
    files.extend(glob.glob(f"{fold}/*"))
    files.extend(glob.glob(f"{fold2}/*"))
    files = list(filter(lambda x: "final__report" not in x,files))
    pds = []
    for f in files:
        pds.append(pd.read_csv(f))
    df = pd.concat(pds)
    df.to_csv("merged.csv")
    print(files)
