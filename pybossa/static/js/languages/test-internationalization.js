
var default_dict = { 
  "test01"     : "Test01 English",
  "test02"     : "Test02 English",
  "test03"     : "Test03 English",
  "button_yes" : "Yes",
  "button_no"  : "No",
  "button_idn" : "I don't know"
}

var en_US_dict = default_dict;

var es_dict={
  "test01"     : "Test01 Spain",
  "test02"     : "Test02 Spain",
  "test03"     : "Test03 Spain",
  "button_yes" : "Si",
  "button_no"  : "No",
  "button_idn" : "No lo se"
}

var pt_dict= {
  "test01"     : "Test01 Portuguese",
  "test02"     : "Test02 Portuguese",
  "test03"     : "Test03 Portuguese",
  "button_yes" : "Sim",
  "button_no"  : "Não",
  "button_idn" : "Não sei"
}

var SesVar = Session("lang");
alert(SesVar);

language = 'pt-BR';

switch(language){
  case 'en-US': var dict = en_US_dict; break;
  case 'pt-BR': var dict = pt_dict;    break;
  case 'es-ES': var dict = es_dict;    break;
  default:      var dict = default_dict;
}

$.i18n.setDictionary(dict);
