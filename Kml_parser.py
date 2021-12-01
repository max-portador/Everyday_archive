


with open('coord.txt', 'r') as f:
    data = f.read()

coord_pairs = data.split()
for i, pair in enumerate(coord_pairs):
    longitude, latitude = pair.split(",")
    longitude = str(360 + float(longitude))
    coord_pairs[i] = f'{longitude},{latitude}'
print(coord_pairs)

with open('coord2.txt', "w") as wf:
    wf.write(" ".join(coord_pairs))