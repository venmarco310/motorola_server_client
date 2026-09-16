# Open a file named 'numbers.txt' in write mode ('w')
with open("./cornell_movie_quotes_corpus/numbers.txt", "w") as file:
    # Loop from 1 to 1,000,000
    for number in range(1, 15000001):
        # Write the number followed by a newline character
        file.write(f"i = {number}\n")

print("File 'numbers.txt' has been created successfully.")