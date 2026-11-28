"""Shared by dblp_pl.py, csr_papers.py and professors_build.py: is a professor CS-related (faculty / unit name)?"""
import os
import re
import sys

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]  # python -I does not add the script's folder; common/ lives in the project root

# A professor counts as CS when the faculty or unit NAME says so (no topic keywords, so a person can check and correct it by looking at the faculty / unit columns):
# informatik / informatics / informatique / computer / software. Faculties that also contain physics (Mainz, Gießen, Cottbus, Osnabrück ...) need the unit to say it.
# Not CS by this rule, on purpose: Wirtschaftsinformatik / business informatics and Medizinische Informatik / medical informatics (also medical data science, digital studies), Elektrotechnik und Informationstechnik (Darmstadt, Chemnitz), Wirtschaftswissenschaften, plain Mathematik, IMTEK / INATECH (Freiburg).
CS_NAME = re.compile(r"(?<!wirtschafts)(?<!medizin)(?<!medizinische )(?<!medical )(?<!business )(?<!geo)informatik|(?<!medical )(?<!business )informatics|informatique|informatica|computer|software", re.I)
ALL_CS = {"CISPA", "Hasso-Plattner-Institut", "MPI-SP", "MPI-SWS", "MPI-INF", "JKU Linz"}  # computer-science institutes / scrapers that read only the CS department, whatever the faculty is called


def cs_hit(p):
    """CS-related by faculty / unit name (see above); CS-only institutes count completely."""
    if p["university"] in ALL_CS:
        return True
    f, u = p["faculty"], p["unit"]
    if re.search(r"Physik|Physics", f):
        return bool(CS_NAME.search(u))
    return bool(CS_NAME.search(f) or CS_NAME.search(u))
