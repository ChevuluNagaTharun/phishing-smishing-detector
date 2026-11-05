import sys, csv

src, out = sys.argv[1], sys.argv[2]
rows = []
with open(src, encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.rstrip("\n")
        if "\t" not in line:
            continue
        label, text = line.split("\t", 1)
        rows.append((text.strip(), 1 if label.strip().lower() == "spam" else 0))

with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["text", "label"])
    w.writerows(rows)
print(len(rows), "rows written to", out)