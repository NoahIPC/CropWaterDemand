"""
This script limits the amount of lag coefficients down to 

"""

# %%
f = open("../../Comparison.mdl", "r")

n = 365 * 40

write = False

all_lines = f.readlines()
f.close()


f2 = open("../../ComparisonCutoff40.mdl", "w")
iterator = all_lines.__iter__()

for line in iterator:
    if 'set s "$o.Lag Coeff"' in line:
        # Check next 5 lines
        lines = [line]
        for i in range(5):
            lines.append(iterator.__next__())

        if (
            '"$s" setColumnLabels {Lag Coeff}' in lines[-1]
            and '"$s" resize 29220 1' in lines[3]
        ):
            lines[3] = f'"$s" resize {n} 1 \n'
            lines[-2] = '"$s" setRowLabels' + "".join([" {}"] * n) + "\n"
            write = True
        f2.writelines(lines)
    elif ("set obj" in line) and write:
        write = False
        f2.write(line)
    elif ('"$s" row' in line) and write:
        if int(line.split(" ")[2]) < n:
            f2.write(line)
    else:
        f2.write(line)

f.close()
f2.close()
# %%
