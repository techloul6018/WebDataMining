# WebDataMining - Architecture Knowledge Graph Extraction

Une pipeline complète pour extraire, traiter et structurer des données d'architecture à partir de sources Web. Ce projet construit un corpus d'architecture, effectue l'extraction d'informations (NER) et établit des relations entre entités pour créer une base de connaissances structurée.

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Utilisation](#utilisation)
- [Phases du projet](#phases-du-projet)
- [Structure du code](#structure-du-code)

## 🎯 Vue d'ensemble

Ce notebook implémente une pipeline de web mining en trois phases principales :

1. **Phase 1 - Web Scraping & Corpus Building** : Extraction et nettoyage du contenu textuel à partir de URLs d'architecture
2. **Phase 2 - Information Extraction** : Extraction d'entités nommées (NER) pour identifier les personnes, organisations, lieux, dates, etc.
3. **Phase 3 - Relation Extraction** : Identification des relations entre entités pour construire un graphe de connaissances


## 📖 Utilisation

### Exécution complète

Le notebook s'exécute en 3 phases successives. Chaque phase peut être exécutée indépendamment si le fichier corpus existe.

### Exécution personnalisée

Vous pouvez modifier les paramètres de chaque phase :

**Phase 1 - Web Scraping & Corpus :**
```python
MIN_WORDS = 500           # Nombre minimum de mots par document
OUTPUT_FILE = "architecture_corpus.jsonl"  # Fichier de sortie
URLS = [...]              # Liste des URLs à scraper
```

**Phase 2 & 3 - NER & Relations :**
```python
TARGET_LABELS = {          # Étiquettes à extraire (Phase 2)
    "PERSON", "ORG", "GPE", "DATE", "WORK_OF_ART", "FAC", "LOC", "EVENT"
}
TARGET_ENTS = {            # Entités pour les relations (Phase 3)
    "PERSON", "ORG", "GPE", "DATE", "WORK_OF_ART", "FAC", "LOC", "EVENT"
}
```

## 🔄 Phases du projet

### Phase 1 : Web Scraping & Construction du Corpus

**Objectif :** Extraire le contenu textuel principal de 14 URLs d'architecture.

**Fonctionnalités :**
- `extract_main_text(url)` : Récupère et nettoie le contenu d'une page Web
- `is_useful(text, min_words)` : Valide la qualité du contenu extraite
- `save_to_jsonl(records, output_path)` : Sauvegarde en format JSONL

**Entrées :**
- 14 URLs sur l'architecture, patrimoine et histoire architecturale

**Sorties :**
- `architecture_corpus.jsonl` : Fichier JSONL avec structure :
  ```json
  {
    "url": "https://...",
    "word_count": 1234,
    "text": "Contenu texte extrait..."
  }
  ```

**Exemples d'URLs traitées :**
- UNESCO World Heritage Sites
- Smarthistory - Global Architecture History
- Fallingwater (Frank Lloyd Wright)
- Le Corbusier & Fondation Le Corbusier
- Architecture Belle Époque française
- Villa Ephrussi de Rothschild
- Villa Kérylos

---

### Phase 2 : Extraction d'Informations (NER)

**Objectif :** Extraire des entités nommées du corpus pour identifier concepts clés.

**Fonctionnalités :**
- `detect_language(text)` : Détecte automatiquement la langue (EN/FR)
- `is_valid_entity(ent)` : Valide les entités selon critères (longueur, type, majuscule)
- `extract_nodes(jsonl_path)` : Extrait toutes les entités par label

**Étiquettes extraites :**
| Label | Description | Exemple |
|-------|-------------|---------|
| `PERSON` | Personnes remarquables | Frank Lloyd Wright, Le Corbusier |
| `ORG` | Organisations, institutions | UNESCO, Fondation Le Corbusier |
| `GPE` | Lieux géographiques | France, Paris, Venice |
| `DATE` | Dates et périodes | 1900-1970, Belle Époque |
| `WORK_OF_ART` | Œuvres architecturales | Fallingwater, Villa Kérylos |
| `EVENT` | Événements historiques | Expositions, conférences |

**Sorties :**
```
PERSON (25 nodes)
  - Frank Lloyd Wright
  - Le Corbusier
  - Gustave Eiffel
  - ...

ORG (18 nodes)
  - UNESCO
  - Fondation Le Corbusier
  - ...
```

**Affichage :** Les 10 premiers nodes de chaque catégorie sont affichés triés alphabétiquement.

**Critères de validation :**
- Minimum 3 caractères
- Au moins une majuscule (pour plupart des labels)
- Exclusion de mots vides génériques

---

### Phase 3 : Extraction de Relations

**Objectif :** Identifier les relations entre entités basées sur la structure syntaxique.

**Fonctionnalités :**
- `extract_edges(jsonl_path)` : Extrait triplets (source, relation, target)
- Analyse syntaxique pour identifier verbes et dépendances
- Support bilingue (EN/FR)

**Structure d'une relation :**
```json
{
  "source": "Entity A",
  "relation": "verb_lemma",
  "target": "Entity B",
  "sentence": "Phrase contexte complète..."
}
```

**Exemple :**
```
1. (Le Corbusier) -> [design] -> (Villa Savoye)
   Context: Le Corbusier a conçu la Villa Savoye...
   
2. (Frank Lloyd Wright) -> [create] -> (Fallingwater)
   Context: Frank Lloyd Wright a créé Fallingwater...
```

**Affichage :** Les premières relations extraites sont affichées avec :
- Numéro séquentiel
- Triplet (source → relation → target)
- Contexte : les 100 premiers caractères de la phrase source



## 💻 Structure du code

### Imports et configuration
```python
import trafilatura, json, spacy
from collections import defaultdict
from typing import Optional, List, Dict, Set
```

### Fonctions principales par phase

**Phase 1 (Web Scraping) :**
- `is_useful(text, min_words)` → bool : Valide la qualité du texte
- `extract_main_text(url)` → Optional[str] : Extrait contenu d'une page
- `save_to_jsonl(records, output_path)` → None : Sauvegarde en JSONL
- `build_corpus(urls)` → None : Pipeline complète Phase 1

**Phase 2 (NER) :**
- `detect_language(text)` → str : Détecte EN ou FR
- `is_valid_entity(ent)` → bool : Valide une entité selon critères
- `extract_nodes(jsonl_path)` → Dict[str, Set[str]] : Extrait toutes entités

**Phase 3 (Relations) :**
- `get_entity_by_token(token, doc)` → Optional[Entity] : Trouve entité au token
- `extract_edges(jsonl_path)` → List[Dict] : Extrait triplets (source, relation, target)




## 📊 Résultats attendus

Après exécution complète :

1. **Corpus** : ~14 documents d'architecture filtrés (>500 mots)
2. **Entités** : Centaines d'entités uniques par catégorie
3. **Relations** : Triplets (source, verbe, target) reliant entités et concepts
