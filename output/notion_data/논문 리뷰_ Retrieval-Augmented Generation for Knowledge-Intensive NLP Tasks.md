# [논문 리뷰] Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

**페이지 ID:** 255d3416-0518-80d2-81c9-c7cc5f499e8a
**생성일:** 2025-08-20T08:02:00.000Z
**마지막 수정:** 2025-08-20T08:02:00.000Z
**URL:** https://www.notion.so/Retrieval-Augmented-Generation-for-Knowledge-Intensive-NLP-Tasks-255d3416051880d281c9c7cc5f499e8a

---

# Abstract

대규모로 사전 훈련된 모델들은 파라미터에 지식을 저장하고, downstream task에 대해서 파인튜닝되었을 때 SOTA를 달성한다. 하지만 LLM의 지식에 접근하고 정확하게 활용하는 능력은 아직 제한적이며, 지식 집약적인 과제들에서는 task-specific한 구조에 비해 성능이 떨어지는 면이 있다. 또한, 결정에 대한 이유를 설명하거나, world knowledge를 업데이트하는 것은 여전히 남아 있는 과제이다. 사전 학습 모델로 하여금 파라미터 내의 지식을 활용하는 것이 아닌 다른 접근법을 취하게 하는 방법은 extractive downstream task들에 대해서만 연구되어 왔다. 이 논문에서는 RAG 모델을 위한 일반적인 파인 튜닝 레시피를 탐색한다. 이 논문에서는 parametric memory 부분이 사전 학습된 seq2seq 모델이고, non-parametric memory는 위키피디아의 dense vector index이고, 사전학습된 뉴럴 retriever로 접근한다. 논문에서는 두 가지 RAG 형식을 비교하는데, 하나는 전체 생성되는 단락이 모두 하나의 리트리벌된 글을 참고하게 하는 것이고, 다른 하나는 토큰별로 다른 글을 참고할 수 있게 하는 것이다. 논문에서는 여러 종류의 지식 집약적 NLP 과제에 대해 파인 튜닝을 진행했고, 세 개의 open domain QA 과제에- 대해 seq2seq 모델과 task-specific retreive-and-extract 구조를 능가하며 SOTA를 달성했다. 생성 과제에 있어서는 RAG 모델이 parametric-only seq2seq SOTA 모델보다 조금 더 구체적이고 다양하며 사실에 기반한 글을 생성하는 것을 관찰했다.

# 1. Introduction

- 사전 훈련된 모델의 한계점
- parametric memory와 non-parametric (retrieval-based) memory를 결합한 하이브리드 모델들
- 논문에서 제안하는 모델
# 2. Methods

### Notations

- x: input sequence
- z: text document to retrieve
- y: target sequence to generate
- → x가 들어왔을 때, y를 생성하기 위해 z를 참고한다
### Components

1. pη(z|x): retreiver
1. pθ(yi|x,z,y1:i−1): generator
- retriever와 generator를 학습하기 위해 retrieved document를 latent variable로 취급한다
# 2.1 Models

### RAG-Sequence Model

- 모델이 sequence내의 각 target token을 예측할 때 같은 문서를 참조하는 접근법
- PRAG-Sequence(y|x)≈∑z∈top−k(p(⋅|x))pη(z|x)pθ(y|x,z)
- PRAG-Sequence(y|x)≈∑z∈top−k(p(⋅|x))pη(z|x)pθ(y|x,z)=∑z∈top−k(p(⋅|x))pη(z|x)ΠNipθ(yi|x,z,yi−1)
### RAG-Token Model

- 모델이 각 토큰을 생성할 때 서로 다른 문서를 참조할 수 있다
- 먼저 retriever를 통해 Top K 개의 문서가 전달되고, generator는 각 document가 주어진 상황에서 다음 토큰을 예측
- PRAG-Token(y|x)≈ΠNi∑z∈top−k(p(⋅|x))pη(z|x)pθ(yi|x,z,yi−1)
# 2.2 Retriever: DPR

- bi-encoder 아키텍쳐
### Notation

- d(z)=BERTd(z)
- q(x)=BERTq(z):
### DPR Architecture

- pη(z|x)∝exp(d(z)⊺q(x))
- top K 개를 뽑는 작업은 MIPS(Maximum Inner Product Search)문제인데, sub-linear 시간 안에 해결 가능
# 2.3 Generator: BART

- BART-large 사용 (400M params)
- input은 x와 z를 concat 해서 사용
# 2.4 Training

- retriever/generator 를 따로 훈련하지 않고 한번에 훈련함
- → retriever는 어떤 문서를 전달해야 하는지 명시적으로 훈련받지 않고, generator가 최종으로 생성하는 결과물에 의해서만 학습된다
- NLL loss: ∑j−logp(yj|xj)
- fine-tuning models: BERTq(query encoder), BART generator
# 2.5 Decoding

### RAG-Token

- 각 시점에서, top-k 문서들과 이전 토큰을 참조해 현재 토큰에 대한 확률을 구하는 방식이기 때문에 기존과 같은 decoding이 가능하다.
- p′θ(yi|x,y1:i−1)=∑z∈top−k(p(⋅|x))pη(z|x)pθ(yi|x,z,yi−1)
### RAG-Sequence

- RAG-Sequence 방법은 각 시점에서 모든 문서를 고려한 해당 토큰의 확률을 구한 후 넘어가는 방법을 채택하지 않고, 반대로 문서를 고정하고 각 문서에 대한 sequence의 확률을 먼저 뽑는다.
- 즉, 토큰을 하나씩 늘려가며 확률을 찾아내는 beam search 방식으로 바로 적용할 수 없다.
- 대신 z에 대한 빔 서치를 함. z가 두 개라고 생각하고 예시를 써 보자.
- 여기에서 marginalize를 하면,
- 그런데 p(y1|z2), p(y4|z1)은 구할 수 없음. (z2를 인풋으로 줬을 때 y1이 나온 적이 없으니까)
# 3. Experiments & 4. Results

# 3.1&4.1 Open-domain Question Answering

- (질문, 답변): (x,y)
- NLL loss사용
- Closed Book QA: parametric knowledge만 활용
- Open Book QA: 검색 활용
- NQ: Natural Questions
- TQA: TriviaQA
- WB: WebQuestions
- CT: CuratedTrec
- CT, WB 데이터셋은 작기 때문에 NQ RAG 모델로 초기화
2, 3, 4에 해당

# 3.2 & 4.2 Abstractive Question Answering

- MSMACO NLG task
- golden passage가 없으면 답변할 수 없는 문제가 많음에도 SOTA에 근접함
- 정성적으로는, 할루시네이션이 적고 BART보다 종종 더 사실에 기반한 답을 생성함
# 3.3&4.3 Jeopardy Question Generation

- 보통 open domain QA 과제에서의 질문들은 짧고 간단하게 구성됨
- Jepordy questions: entity에 대한 사실을 통해 entity를 예측하는 질문
- human evaluation
- RAG-Token 정량/정성적으로 더 좋은 성능을 얻음
- RAG-Token이 더 좋은 성능을 얻은 이유는, Jeopardy 질문들이 서로 다른 두 정보를 결합할 때가 있기 때문으로 추정됨.
# 4.4 Fact Verification

- FEVER:
- FVR3
- FVR2
- RAG 모델에서 리트리벌된 문장이 gold evidence sentence와 overlap이 있었음
# 4.5 Additional Results

### Generation Diversity

- RAG 모델이 좀 더 다양한 trigram을 사용해서 생성함
### Retrieval Ablations

- RAG 모델의 키 피쳐 중 하나는 관련된 문서를 retreive하도록 훈련하는 것. 이것이 잘 되었는지 검증하기 위해 트레이닝 과정에서 retriever를 freeze한다.
- FEVER에서는 BM25가 더 좋은 결과를 내는데, FEVER의 주장들이 entity 중심이기 때문에 word-overlap based retrieval에 적합할 수 있다고 함.
### Index hot-swapping

- 2016년 12월의 Wikipedia dump로 만든 index와 2018년 12월의 Wikipedia dump로 만든 index를 비교함
- 이 기간동안 바뀐 82명의 세계 지도자의 리스트를 가지고, “Who is {position}?” 질문으로 평가
- 이 실험을 통해 단순히 단순히 index 를 대체함으로서 RAG의 world knowledge를 대체할 수 있다는 것을 보여줌
### Effect of Retrieving more document

- 검색되는 문서의 수를 5개/10개로 실험해 보았는데 큰 성능차이는 없었음.
