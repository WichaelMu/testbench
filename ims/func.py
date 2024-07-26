import sys;
import json;
from functional import seq;

def exec ():
	F = open ("gamedev.json", "r");
	C = json.load (F);

	CO = C["courses"]

	CRICOS = seq (CO) \
		.map (lambda x: x["codes"]) \
		.reduce (lambda x, y: x + y) \
		.filter (lambda x: x["type"].get ("label", "") == "CRICOS") \
		.map (lambda x: x["code"]) \
		.to_list ();

	CPC = seq (CO) \
		.map (lambda x: x["award"]) \
		.reduce (lambda x, y: x + y) \
		.map (lambda x: x["award_title"]) \
		.to_list ();

	ENGREQ = seq (CO) \
		.map (lambda x: x["requirement"]) \
		.reduce (lambda x, y: x + y) \
		.filter (lambda x: x.get ("requirement_multi_1", None) is not None) \
		.filter (lambda x: [ i.get ("value", "").startswith ("ELR") for i in x["requirement_multi_1"] ]) \
		.filter (lambda x: x["type"].get ("value", "") == "english_language_requirement") \
		.map (lambda x: seq (x["requirement_multi_1"]).map (lambda x: x["label"])) \
		.map (lambda x: x.map (lambda x: x.replace ("\n\n", "; or "))) \
		.reduce (lambda x, y: x + y) \
		.to_list ()

	ENTREQ = seq (CO) \
		.map (lambda x: x["requirement"]) \
		.reduce (lambda x, y: x + y) \
		.filter (lambda x: x["type"].get ("value", "") == "admission") \
		.map (lambda x: x.get ("description", "")) \
		.filter (lambda x: x != "") \
		.to_list ()
	print (ENGREQ);

if (__name__ == "__main__"):
	exec();
	sys.exit (0);
