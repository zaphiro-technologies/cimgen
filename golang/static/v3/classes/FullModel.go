package classes

type FullModel struct {
	About                string    `xml:"about,attr"`
	ModelingAuthoritySet string    `xml:"http://iec.ch/TC57/61970-552/ModelDescription/1# Model.modelingAuthoritySet"`
	DependentOn          Reference `xml:"http://iec.ch/TC57/61970-552/ModelDescription/1# Model.DependentOn"`
	Profile              []string  `xml:"http://iec.ch/TC57/61970-552/ModelDescription/1# Model.profile"`
	Description          string    `xml:"http://iec.ch/TC57/61970-552/ModelDescription/1# Model.description"`
	Version              int       `xml:"http://iec.ch/TC57/61970-552/ModelDescription/1# Model.version"`
	ScenarioTime         string    `xml:"http://iec.ch/TC57/61970-552/ModelDescription/1# Model.scenarioTime"`
	Created              string    `xml:"http://iec.ch/TC57/61970-552/ModelDescription/1# Model.created"`
}
