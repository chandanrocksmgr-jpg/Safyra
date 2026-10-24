/** Mirrors backend models/information.py. */
export interface InformationSection {
  id: string;
  label: string;
  title: string;
  text: string;
}

export interface InformationFaq {
  question: string;
  answer: string;
}

export interface InformationContent {
  eyebrow: string;
  title: string;
  title_emphasis: string;
  intro: string;
  sections: InformationSection[];
  faq_title: string;
  faqs: InformationFaq[];
  help_label: string;
  help_message: string;
}
