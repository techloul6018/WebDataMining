"""
src/ie/ner.py
Named Entity Recognition & Relation Extraction pipeline.
Domain: Science-Fiction (authors & works)
"""

import spacy
import pandas as pd

# ── Configuration ──
ENTITY_TYPES          = ["PERSON", "ORG", "GPE", "WORK_OF_ART", "DATE"]
RELATION_ENTITY_TYPES = ["PERSON", "ORG", "GPE", "WORK_OF_ART"]
MAX_TEXT_LENGTH       = 5000   # transformer token limit safeguard
OUTPUT_CSV            = "extracted_knowledge_scifi.csv"
RELATIONS_CSV         = "extracted_relations_scifi.csv"


def load_nlp_model(model_name: str = "en_core_web_trf"):
    """Load a spaCy NLP model."""
    nlp = spacy.load(model_name)
    print(f"spaCy model loaded: {nlp.meta['name']}")
    return nlp


def extract_entities(data: list, nlp, output_csv: str = OUTPUT_CSV) -> pd.DataFrame:
    """
    Run NER on crawled pages.
    Returns a deduplicated DataFrame of (entity, type, source_url).
    Saves results to CSV.
    """
    records = []

    for entry in data:
        url  = entry["url"]
        text = entry["text"][:MAX_TEXT_LENGTH]
        doc  = nlp(text)

        for ent in doc.ents:
            if ent.label_ in ENTITY_TYPES:
                records.append({
                    "entity":     ent.text.strip(),
                    "type":       ent.label_,
                    "source_url": url
                })

        print(f"✓ {url.split('/')[-1]:<40} {len([r for r in records if r['source_url']==url])} entities")

    df = pd.DataFrame(records).drop_duplicates()
    df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"\nTotal unique entities: {len(df)} → saved to {output_csv}")
    return df


def extract_relations(data: list, nlp, output_csv: str = RELATIONS_CSV) -> pd.DataFrame:
    """
    Extract (subject, relation, object) triples via dependency parsing.
    Returns a deduplicated DataFrame.
    """
    triples = []

    for entry in data:
        doc = nlp(entry["text"][:10000])

        for sent in doc.sents:
            ents_in_sent = [
                ent for ent in sent.ents
                if ent.label_ in RELATION_ENTITY_TYPES
            ]

            if len(ents_in_sent) < 2:
                continue

            for token in sent:
                if token.pos_ == "VERB":
                    subj_tokens = [w for w in token.lefts  if w.dep_ in ("nsubj", "nsubjpass")]
                    obj_tokens  = [w for w in token.rights if w.dep_ in ("dobj", "pobj")]

                    if subj_tokens and obj_tokens:
                        triples.append({
                            "subject":    subj_tokens[0].text,
                            "relation":   token.lemma_,
                            "object":     obj_tokens[0].text,
                            "sentence":   sent.text.strip()[:150],
                            "source_url": entry["url"]
                        })

    df = pd.DataFrame(triples).drop_duplicates(subset=["subject", "relation", "object"])
    df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"Extracted {len(df)} unique triples → saved to {output_csv}")
    return df
