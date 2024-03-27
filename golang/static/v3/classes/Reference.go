package classes

import "strings"

type Reference struct {
	Text     string `xml:",chardata"`
	Resource string `xml:"http://www.w3.org/1999/02/22-rdf-syntax-ns# resource,attr"`
}

func RemoveRDFCharacters(s string) string {
	return strings.TrimLeft(s, "#_")
}
