/** Mirrors backend models/about.py. */
export interface AboutStorySection {
  heading: string;
  body: string;
  image_url: string;
}

export interface AboutValue {
  title: string;
  body: string;
}

export interface AboutFounder {
  name: string;
  role: string;
  quote: string;
  body: string;
  image_url: string;
}

export interface AboutContent {
  eyebrow: string;
  title: string;
  title_emphasis: string;
  intro: string;
  hero_image_url: string;
  story_sections: AboutStorySection[];
  values_title: string;
  values: AboutValue[];
  founder: AboutFounder;
  cta_label: string;
  cta_message: string;
}
