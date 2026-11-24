# Neuroscience foundations for the Cerepath Digital Mind

## Scientific scope

There is no complete, universally accepted engineering blueprint of the human mind, and no finite implementation can incorporate "all neuroscience papers." This document records selected foundational studies and reviews that inform the current architecture and future research directions.

Cerepath implements **cognitive analogies and testable computational mechanisms**. Python classes named after brain systems do not reproduce biological structures, neural dynamics, subjective experience, emotions, or consciousness. Passing software tests demonstrates specified software behaviour, not biological equivalence.

## Evidence-to-implementation map

| Cognitive topic | Research foundation | Cerepath implementation | Scientific boundary |
|---|---|---|---|
| Working memory | Baddeley & Hitch (1974); Baddeley (2000, 2012) | `BaddeleyWorkingMemory`: bounded recent dialogue context | Item/character budgets are engineering limits, not neural capacity measurements |
| Episodic and semantic memory | Tulving (1972) | `HippocampalIndexer` preserves lesson episode identity/provenance; `semantic_knowledge` stores owner-taught concepts; `knowledge_sources` and `knowledge_chunks` preserve document episodes and passages | Database rows and content hashes are not hippocampal engrams |
| Complementary learning systems | McClelland, McNaughton & O'Reilly (1995); O'Reilly et al. (2014) | Separate experience traces from durable semantic records; design boundary for future offline consolidation | No hippocampal-neocortical circuit, neural replay or gradual cortical learning is simulated |
| Selective attention | Desimone & Duncan (1995); Lindsay (2020) | `PrefrontalCognitiveController` ranks relevant records under a context budget | Deterministic ranking is not neural biased competition |
| Executive control | Miller & Cohen (2001); Miyake et al. (2000) | Goal-conditioned context selection and distinct feedback/evidence checks | Not a full model of executive function |
| Predictive coding | Rao & Ballard (1999); Friston (2010) | Research direction for future explicit prediction and sensory prediction-error modules | Predictive coding/free-energy accounts are influential theoretical frameworks, not settled descriptions of the whole mind |
| Reward prediction error | Schultz, Dayan & Montague (1997) | `RewardPredictionError` logs observed-minus-expected owner feedback | A software metric is not dopamine, reward feeling or a biological learning signal |
| Metacognition | Flavell (1979); Nelson & Narens (1990) | `MetacognitiveMonitor` exposes retrieval coverage and missing evidence | Retrieval coverage is not answer truth probability or self-awareness |
| Sleep and systems consolidation | Rasch & Born (2013); Klinzing, Niethard & Born (2019) | Research basis for future replay/consolidation jobs | Cerepath does not sleep; scheduled database work is only a computational analogy |
| Reconsolidation | Nader, Schafe & LeDoux (2000) | Incorrect owner-flagged knowledge moves to `needs_review`; feedback remains in experience history | The cited experiment concerns reactivated fear memories in rats; it does not establish that every memory updates this way |
| Episodic recall | Tulving (1972); McClelland et al. (1995) | Completed dialogue is retained as a source-linked episode and can be recalled across conversations | A stored dialogue record is not a hippocampal engram; no neural replay is simulated |
| Retrieval practice | Karpicke & Roediger (2008) | Owner attempts recall, reveals the answer, and rates performance | Owner ratings are not objective tests of memory or intelligence |
| Spaced practice | Cepeda et al. (2006) | `SM2SpacedRepetitionScheduler` sets review intervals based on self-rated retrieval success | The SM-2 algorithm is an engineering heuristic; it is not a biological model or a personalized clinical learning prescription |
| Synaptic plasticity and cell assemblies | Hebb (1949); Seung (2000) | Repeated teaching increments reinforcement count; corrections remain traceable | No artificial synapses, neuron model or biological plasticity is implemented |
| Neuroscience-inspired AI | Hassabis et al. (2017) | Overall research-to-engineering approach | Inspiration is not replication |

## Current computational subsystems

- **Working memory:** recent conversation context is constrained by item and character budgets before model prompting.
- **Hippocampal indexing analogy:** normalized lesson content gets a stable SHA-256 trace to make repeated owner teaching idempotent and preserve provenance.
- **Semantic memory:** owner-taught facts, concepts, procedures, skills, preferences and principles are stored separately from transient conversation turns. Uploaded learning materials retain original bytes, extracted text, source hashes and chunk/page provenance.
- **Episodic memory:** completed conversations are encoded as owner-scoped episodes linked to the original chat messages. Lexical and optional local-vector recall can retrieve previous experiences, and recall counters are updated.
- **Retrieval practice and spacing:** owner-rated recall schedules use a transparent SM-2-inspired interval heuristic. The mastery value is a self-report signal and not a factual confidence score.
- **Local semantic retrieval:** optional Ollama embeddings (`all-minilm`, 384 dimensions) complement PostgreSQL full-text ranking. Without local Ollama, text retrieval still works; no remote embedding service is used.
- **Knowledge graph:** canonical concepts and typed relations are persisted separately. Relations require an explicit owner action and preserve evidence/source references; the software does not silently invent concept edges.
- **Prefrontal attention analogy:** a deterministic relevance controller combines lexical overlap, database retrieval score, confidence and reinforcement count. Relevance dominates; an unrelated record is not selected just because its confidence is high.
- **Metacognitive monitoring:** retrieval is labelled strong, partial, weak or absent. These labels describe retrieval coverage only.
- **Feedback signal:** explicit owner feedback produces an observed-minus-expected reward metric. Incorrect knowledge is quarantined for review, not silently rewritten.

## Selected bibliography

1. Baddeley, A. D., & Hitch, G. (1974). Working Memory. *Psychology of Learning and Motivation*, 8, 47–89. https://doi.org/10.1016/S0079-7421(08)60452-1
2. Baddeley, A. (2000). The episodic buffer: a new component of working memory? *Trends in Cognitive Sciences*, 4(11), 417–423. https://doi.org/10.1016/S1364-6613(00)01538-2
3. Baddeley, A. (2012). Working Memory: Theories, Models, and Controversies. *Annual Review of Psychology*, 63, 1–29. https://doi.org/10.1146/annurev-psych-120710-100422
4. Tulving, E. (1972). Episodic and semantic memory. In *Organization of Memory*, 381–403. Academic Press.
5. McClelland, J. L., McNaughton, B. L., & O'Reilly, R. C. (1995). Why there are complementary learning systems in the hippocampus and neocortex. *Psychological Review*, 102(3), 419–457. https://doi.org/10.1037/0033-295X.102.3.419
6. O'Reilly, R. C., Bhattacharyya, R., Howard, M. D., & Ketz, N. (2014). Complementary Learning Systems. *Cognitive Science*, 38(6), 1229–1248. https://doi.org/10.1111/j.1551-6709.2011.01214.x
7. Desimone, R., & Duncan, J. (1995). Neural mechanisms of selective visual attention. *Annual Review of Neuroscience*, 18, 193–222. https://doi.org/10.1146/annurev.ne.18.030195.001205
8. Lindsay, G. W. (2020). Attention in Psychology, Neuroscience, and Machine Learning. *Frontiers in Computational Neuroscience*, 14, 29. https://doi.org/10.3389/fncom.2020.00029
9. Miller, E. K., & Cohen, J. D. (2001). An integrative theory of prefrontal cortex function. *Annual Review of Neuroscience*, 24, 167–202. https://doi.org/10.1146/annurev.neuro.24.1.167
10. Miyake, A., et al. (2000). The unity and diversity of executive functions. *Cognitive Psychology*, 41(1), 49–100. https://doi.org/10.1006/cogp.1999.0734
11. Rao, R. P. N., & Ballard, D. H. (1999). Predictive coding in the visual cortex. *Nature Neuroscience*, 2, 79–87. https://doi.org/10.1038/4580
12. Friston, K. (2010). The free-energy principle: a unified brain theory? *Nature Reviews Neuroscience*, 11, 127–138. https://doi.org/10.1038/nrn2787
13. Schultz, W., Dayan, P., & Montague, P. R. (1997). A neural substrate of prediction and reward. *Science*, 275(5306), 1593–1599. https://doi.org/10.1126/science.275.5306.1593
14. Flavell, J. H. (1979). Metacognition and cognitive monitoring. *American Psychologist*, 34(10), 906–911. https://doi.org/10.1037/0003-066X.34.10.906
15. Nelson, T. O., & Narens, L. (1990). Metamemory: A theoretical framework and new findings. In *The Psychology of Learning and Motivation*, 26, 125–173.
16. Rasch, B., & Born, J. (2013). About sleep's role in memory. *Physiological Reviews*, 93(2), 681–766. https://doi.org/10.1152/physrev.00032.2012
17. Klinzing, J. G., Niethard, N., & Born, J. (2019). Mechanisms of systems memory consolidation during sleep. *Nature Neuroscience*, 22, 1598–1610. https://doi.org/10.1038/s41593-019-0467-3
18. Nader, K., Schafe, G. E., & LeDoux, J. E. (2000). Fear memories require protein synthesis in the amygdala for reconsolidation after retrieval. *Nature*, 406, 722–726. https://doi.org/10.1038/35021052
19. Hebb, D. O. (1949). *The Organization of Behavior: A Neuropsychological Theory*. Wiley.
20. Seung, H. S. (2000). Half a century of Hebb. *Nature Neuroscience*, 3, 1166. https://doi.org/10.1038/81430
21. Hassabis, D., Kumaran, D., Summerfield, C., & Botvinick, M. (2017). Neuroscience-Inspired Artificial Intelligence. *Neuron*, 95(2), 245–258. https://doi.org/10.1016/j.neuron.2017.06.011
22. Karpicke, J. D., & Roediger, H. L. (2008). The critical importance of retrieval for learning. *Science*, 319(5865), 966–968. https://doi.org/10.1126/science.1152408
23. Cepeda, N. J., Pashler, H., Vul, E., Wixted, J. T., & Rohrer, D. (2006). Distributed practice in verbal recall tasks: A review and quantitative synthesis. *Psychological Bulletin*, 132(3), 354–380. https://doi.org/10.1037/0033-2909.132.3.354

## Deliberate non-implementations

The following are research topics, not current product capabilities: predictive coding networks, global neuronal workspace, affective/emotional systems, embodied sensorimotor models, sleep-like replay, automatic reconsolidation, neural plasticity, and consciousness. They need separate evidence reviews, measurable tasks, safety constraints and evaluation before implementation.

## Milestone status

The current cognitive-kernel release implements bounded working memory, source-linked episodic memory, owner-taught semantic knowledge, document ingestion and chunking, optional local embeddings, lexical/vector hybrid recall, owner-managed concept relationships, deterministic attention ranking, explicit feedback, retrieval-evidence monitoring and user-rated spaced retrieval practice. It does not implement a biological neural network, autonomous self-modification, sleep-like replay, or consciousness.
