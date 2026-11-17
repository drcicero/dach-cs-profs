"""Shared by dblp_pl.py and professors_build.py: is a professor CS-related (pure CS faculty, or a CS keyword in topic / unit)?"""
import os
import re
import sys

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")]  # python -I does not add the script's folder; common/ lives in the project root
from common.cs import CS

CS_FACULTY = re.compile(r"^(?:KIT-)?(?:Fakultät(?: für| 5,)?|Fachbereich|Institut für|Department of)?\s*(?:Fachbereich )?Informatik$|^Institut für Informatik$"
                        r"|Computer Science|Computer and Communication Sciences|^(?:Department|Faculty|School) (?:of|for) Informatics|Département d.informatique|Institut d.informatique"  # CH / AT / international names
                        r"|^Max Planck Institute for (?:Software Systems|Security and Privacy|Informatics)|^CISPA|^Fakultät für Informatik und Biomedizinische Technik|^Technisch-Naturwissenschaftliche Fakultät|^Department Mathematik und Informatik")


def cs_hit(p):
    """CS-related: the faculty is a pure computer-science one, or a CS keyword stands in the topic / unit (broad faculties such as ETIT, MIN or Math+CS say nothing)."""
    m = CS.search(p["topic"] + " | " + p["unit"])
    return bool(CS_FACULTY.search(p["faculty"]) or m)
