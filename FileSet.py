# a set of strings, populated from a file
class FileSet(set):
    def __init__(self, filename):
        """
        Initialize the FiledSet instance by reading lines from a text file.
        Each line in the file will be treated as an entry in the set.
        :param filename: Path to the text file.
        """
        super().__init__()
        try:
            with open(filename, 'r') as file:
                for line in file:
                    stripped_line = line.strip()
                    if stripped_line != '':
                       self.add(stripped_line)
        except FileNotFoundError:
            raise ValueError(f"The file '{filename}' was not found.")
        except IOError as e:
            raise ValueError(f"An error occurred while reading the file: {e}")

if __name__ == '__main__':
    fset = FileSet('whitelist.txt')
    print(fset)
    print('123' in fset)