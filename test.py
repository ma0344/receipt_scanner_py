
letter = []
for i in range(0, 9):
    letter.append((','.join([chr(val) for val in range((48 + i * 8) + i, (56 + i * 8) + i)])))

csv_str = '\n'.join(letter)
print(csv_str)
print(120 - 48)
