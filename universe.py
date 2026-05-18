import io
import logging

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Fallback list — used if Wikipedia is unreachable
_FALLBACK_SP500 = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","BRK-B","LLY","AVGO",
    "JPM","TSLA","UNH","XOM","V","MA","PG","JNJ","HD","MRK","COST","ABBV",
    "CVX","CRM","BAC","NFLX","AMD","PEP","KO","TMO","ACN","WMT","MCD","ABT",
    "LIN","DHR","TXN","ORCL","PM","ADBE","NEE","QCOM","RTX","GE","AMGN","IBM",
    "SPGI","CAT","INTU","LOW","HON","UNP","AMAT","GS","ELV","BKNG","ISRG","SYK",
    "MDT","VRTX","T","BLK","PLD","REGN","CB","GILD","C","ADI","MDLZ","AXP",
    "SBUX","MO","LRCX","CI","SO","TJX","ETN","DE","ZTS","BMY","SCHW","DUK",
    "BSX","KLAC","PGR","AON","NOC","ITW","SLB","CME","MMC","PH","SNPS","CDNS",
    "WM","FCX","GD","APH","FI","MCO","EMR","EOG","MPC","PSX","OXY","HCA","CL",
    "USB","MSI","ORLY","ADP","NSC","MCK","CTAS","ICE","EW","PCAR","NKE","TGT",
    "WELL","TDG","ECL","DXCM","ROP","CARR","MNST","SHW","APD","OKE","AIG","AFL",
    "PSA","NEM","D","HLT","WBA","F","GM","NXPI","MCHP","PAYX","ROST","STZ",
    "AEP","KMB","HES","PEG","HSY","TEL","ODFL","GWW","VRSK","EXC","XEL","CTSH",
    "EBAY","GEHC","CSGP","IDXX","ACGL","WEC","FAST","MSCI","VLO","DVN","FANG",
    "PPG","IQV","KEYS","OTIS","CPRT","BKR","GLW","AME","ANSS","IR","ALB","EPAM",
    "WAB","DLTR","HPQ","KHC","ON","TROW","FTV","DOW","LHX","LYB","APTV","OMC",
    "LDOS","EXPD","CBOE","MTD","WAT","TTWO","FDS","BR","AKAM","TER","MPWR","ENPH",
    "TSCO","ULTA","BALL","PKI","IEX","COO","TECH","TYL","GPC","NTAP","HOLX",
    "SWKS","ZBRA","CTLT","LW","JBHT","SNA","HSIC","POOL","FFIV","RE","QRVO",
    "PNR","ALLE","HII","AOS","NDSN","MAS","TXT","ROL","BWA","HRL","CPB","LKQ",
    "NVR","PHM","DHI","LEN","TOL","MTH","TPR","RL","PVH","HBI","GPS","LB",
    "WRK","IP","PKG","CF","MOS","FMC","CE","EMN","AXON","GNRC","TT","CHRW",
    "EXPD","XYL","RRX","PTC","PAYC","TRMB","VRSN","JKHY","CTXS","INCY","BIIB",
    "ALGN","DXCM","PODD","MTCH","ZM","DOCU","OKTA","SNOW","PLTR","COIN","RBLX",
    "UBER","LYFT","DASH","ABNB","NET","CRWD","DDOG","S","MDB","GTLB","PATH",
    "SPG","O","VICI","AMT","CCI","EQIX","DLR","SBAC","IRM","WY","AVB","EQR",
    "ESS","UDR","CPT","MAA","NNN","FR","EGP","STAG","TRNO","COLD","REXR",
]

_FALLBACK_SP400 = [
    "AXTA","BWXT","CACC","CASY","CBRE","CFG","CHRW","CLF","COLM","CPE","CRI",
    "CRL","CVLT","DAL","DKS","DT","DVA","ELAN","ENTG","EQT","ETSY","EWBC",
    "EXAS","EXLS","EXR","FAF","FICO","FHN","FN","FNF","FND","FNV","FSLR",
    "GBCI","GGG","GLOB","GMS","HAE","HEI","HFC","HGV","HP","HPE","HZNP",
    "IAA","IART","IBOC","IDCC","IDA","IHRT","INGR","INVA","JAZZ","JEF","JNPR",
    "KBH","KEX","KNX","KRC","LANC","LECO","LEG","LFUS","LII","LITE","LKFN",
    "LNTH","LNW","M","MAN","MASI","MATX","MBIN","MED","MEDP","MELI","MMSI",
    "MMS","MODG","MOH","MORN","MRC","MSA","MSGS","MTG","MTN","MTSI","MUR",
    "NATI","NBR","NBTB","NEOG","NEU","NFG","NFLX","NJR","NNN","NOVT","NRG",
    "NSA","NSP","NVST","NVT","OGS","OHI","OII","OLED","OLN","OMCL","OMF",
    "ONTO","ORA","ORCL","OSK","OTTR","OUT","OZK","PAYA","PCVX","PDCO","PEN",
    "PII","PNM","POST","POWL","PRA","PRG","PRGO","PRKS","PRMW","PRSP","PSB",
    "PSMT","PTCT","PTEN","PTVE","PVH","RBC","RGEN","RLI","RNR","RRC","RS",
    "RUSHA","RXO","SAIA","SANM","SCI","SEE","SF","SFIX","SFM","SGMS","SHAK",
    "SIGI","SITE","SJM","SKX","SLGN","SM","SMG","SNV","SOLV","SPB","SSNC",
    "STEL","STLD","SUM","SWX","SYNA","SYF","TCBI","TFSL","TFX","THG","TNET",
    "TNL","TOST","TOWN","TREX","TRIP","TRMK","TROW","TRST","TRU","TRUP","TRVG",
    "TSN","TTC","TTEC","TTGT","TWNK","TXG","UGI","UNF","UNFI","USFD","USPH",
    "VCEL","VCRA","VEEV","VIRT","VMEO","VSH","VSCO","VVV","WDFC","WEN","WHR",
    "WIRE","WMS","WOR","WRB","WSFS","WTS","WW","XPO","XRAY","XRX","YELP","ZI",
]


def _fetch_wikipedia_tickers(url: str, symbol_col: str = "Symbol") -> list[str]:
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        tables = pd.read_html(io.StringIO(resp.text), attrs={"id": "constituents"})
        if tables:
            return tables[0][symbol_col].tolist()
        # fallback: try any table with a Symbol column
        tables = pd.read_html(io.StringIO(resp.text))
        for t in tables:
            if symbol_col in t.columns:
                return t[symbol_col].tolist()
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
    return []


def get_universe() -> list[str]:
    sp500 = _fetch_wikipedia_tickers(
        "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    )
    sp400 = _fetch_wikipedia_tickers(
        "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies"
    )

    if not sp500:
        logger.warning("Wikipedia blocked — using built-in fallback ticker list")
        sp500 = _FALLBACK_SP500
        sp400 = _FALLBACK_SP400

    all_tickers = list({t.replace(".", "-") for t in sp500 + sp400})
    logger.info(f"Universe: {len(all_tickers)} tickers (SP500={len(sp500)}, SP400={len(sp400)})")
    return all_tickers
