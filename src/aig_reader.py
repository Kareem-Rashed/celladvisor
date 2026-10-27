
def lit_to_var(lit):
    return (lit>>1)

def is_inverted(lit):
    return (lit&1)


def read_aag(file):
    lines = file.split("\n") 
    parts = lines[0].split()  
    num_inputs = int(parts[2])
    num_latches = int(parts[3])
    num_outputs = int(parts[4])
    num_ands = int(parts[5])     # these are MILOA, same every file


    position = 1                          # line 0 is the header, inputs start at line 1

    sources = []
    for Sline in range(num_inputs):           
        lit = int(lines[position])        
        sources.append(lit_to_var(lit))   
        position += 1                     

    for Lline in range(num_latches):
        first = int(lines[position].split()[0])   
        sources.append(lit_to_var(first))         #latch output is technically a source
        position += 1

    position += num_outputs  # dont need them for cuts


    ands = {}
    for Aline in range(num_ands):
        OutputA, InputA, InputB = lines[position].split()
        ands[lit_to_var(int(OutputA))] = (int(InputA), int(InputB))
        position += 1

    return sources, ands


