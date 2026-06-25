import subprocess
import sys


def extract(pdf_path: str, out_path: str) -> None:
    subprocess.run(["pdftotext", pdf_path, out_path], check=True)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: extract.py <pdf> <out.txt>")
        raise SystemExit(2)
    extract(sys.argv[1], sys.argv[2])
