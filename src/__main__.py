import src
import logging
import asyncio
from translatepy import Language

# TODO: level -> exp n words known (like C2->15k, C1->8k, B2->5k, B1->2.5k, A2->1k, A1->500)


def main():
	logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
	src.L = logging.getLogger(__name__)

	# TODO: allow for submission through stdin
	text = "Hmm... ich spüre hinter diesem ganzen Spektakel mehrere Schichten. In erster Linie müssen die Lehrer uns entwaffnen. Aber das hätte viel einfacher und mit weniger Problemen gemacht werden können. Sie hätten Jungen und Mädchen in getrennte Räume gebracht, sie gründlich durchsucht und das wäre alles gewesen. Aber die Verwaltung zog einen schwierigeren Weg vor, es sind sofort mehrere erzieherische Momente zu erkennen."

	out = asyncio.run(src.translate_infrequent(text, Language("de"), 10_000))
	print(out)


main()
