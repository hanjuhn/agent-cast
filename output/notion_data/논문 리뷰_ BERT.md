# [논문 리뷰] BERT

**페이지 ID:** 255d3416-0518-809a-a993-c168289ba55d
**생성일:** 2025-08-20T08:01:00.000Z
**마지막 수정:** 2025-08-20T08:02:00.000Z
**URL:** https://www.notion.so/BERT-255d34160518809aa993c168289ba55d

---

### BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding

Jacob Devlin, Ming-Wei Chang, Kenton Lee, Kristina Toutanova

# Abstract

BERT = Bidirectional Encoder Representations from Transformers

Attention Is All You Need에서 소개한 Transformer 구조를 활용한 Language Representation에 관한 논문이다. BERT는 모든 layer에서 left과 right context을 같이 고려함으로써 unlabeled text에서 양방향 심층 표현을 pre-train하도록 설계되었다. 결과적으로, pre-trained BERT는 output layer 추가와 fine-tuning(전이학습)을 통해 question answering 또는 language inference 같은 다양한 NLP task에서 SOTA를 달성하였다.

# 1. Introduction

NLP task 종류

- sentence-level task : natural language inference, paraphrasing. 문장 간의 관계를 예측.
- token-level task : named entity recognition, question answering. 모델은 token level에서 세밀한 결과(fine-grained output)를 생산해야 된다.
### 연구의 중요성

Language model pre-training은 여러 NLP task를 향상시키는데 탁월하다.

### 최근 연구 현황

pre-trained language representations을 적용하는 방식

- feature-based approach : ex) ELMo. task-specific network에 pre-trained language representation을 추가적인 feature로 제공함.
- fine-tuning approach : ex) GPT. task-specific한 파라피터를 최소로 하고 모든 pre-trained된 파라미터를 downstream task를 학습을 통해 조금만 바꿔주는 방식
### 선형 연구의 한계점

일반적인 langauge model(ELMo, GPT)은 단방향(unidirectional) 또는 shallow bidirectional(단방향 + 단방향) 이기 때문에 pre-training에서 사용되는 아키텍처의 선택에 제한이 있다.

예) GPT에서 오직 left-to-right 구조(Transformer decoder 구조)를 사용하고 모든 토큰은 오직 이전 토큰만 고려한다. sentence level task에서는 차선책이지만 token-level task에서는 매우 좋지 않은 방법이다.

### 연구 내용 요약

1. masked language model(MLM)을 사용하여 deep bidirectional 구조를 가진다. BERT는 input token 전체과 masked token을 한번에 Transformer encoder에 넣고 원래 token을 예측하므로 deep bidirectional하다.
1. pre-trained representations이 고도로 엔지니어링된 많은 작업별(task-specific) 아키텍처의 필요성을 감소시킨다는 것을 보여준다.
1. BERT는 11개 NLP task에서 SOTA를 달성하였다
# 2. Related Work

### 2.1 Unspervised Feature-based Approaches

ELMo, LSTM

### 2.2 Unsupervised Fine-tuning Approaches

OpenAI GPT(Generative Pre-trained Transformer)는 이전 단어들이 주어졌을 때 다음 단어가 무엇인지를 맞추는 과정에서 pre-trained한다. 구조는 Transformer decoder만 사용하고 문장 시작부터 순차적으로 계산한다는 점에서 일방향(unidirectional)이다. GPT는 문장 생성에 강점을 지녔다.

### 2.3 Transfer Learning from Supervised Data

대용량 dataset을 사용하는 supervised tasks(natural language inference, machine translation)로부터 효과적인 transfer learning을 보여준다.

# 3. BERT

BERT의 아키텍처는 Transformer 구조를 사용하지만, pre-training과 fine-tuning 시의 아키텍처를 조금 다르게하여 transfer learning을 용이하게 만드는 것이 핵심이다.

Model Architecture

- multi-layer bidirectional Transformer encoder 구조 (Attention Is All You Need or tensor2tensor library 참조)
- BERT는 모델의 크기에 따라 base 모델과 large 모델로 나뉜다.
- BERT_base 모델은 OpenAI GPT 모델과 hyper parameter가 동일하다. OpenAI GPT 모델은 제한된 self-attention을 수행하는 transformer decoder 구조이지만, BERT는 MLM과 NSP를 위해 self-attention을 수행하는 transformer encoder 구조이다.
Input/Output Representations

Figure 2. BERT input representation

- BERT의 input은 3가지 embedding 합으로 이루어진다.
- WordPiece embedding을 사용한다. WordPiece(Wu et al., 2016)
- 모든 문장의 첫번째 token은 [CLS]이다. 전체의 transformer 층을 다 거치고 난 뒤의 이러한 [CLS] token은 총합한 token sequence라는 걸 의미한다. classification task 경우, 단일 문장 또는 연속한 문장의 classification을 쉽게 할 수 있다.
- setence pair는 하나의 문장으로 묶어져 입력된다. 문장을 구분하기 위해 2가지 방식을 사용한다. [SEP] token을 사용하거나 segment embedding을 사용하여 sentence A 또는 sentence B embeddng을 더해준다.
### 3.1 Pre-training BERT

ELMo와 GPT는 left-to-right 또는 right-to-left 언어 모델을 사용하여 pre-training을 수행한다. 하지만, BERT는 이와 다르게 2가지의 새로운 unsupervised task로 pre-training을 수행한다.

Task #1. Masked LM

input token 중 랜덤하게 mask하고 이를 학습하여 주변 단어의 context만 보고 masked token을 예측한다.

- 각 문장에서 랜덤하게 15% 비율로 [MASK] token으로 바꾸어준다.
- text를 tokenization하는 방법은 WordPiece를 사용한다.
- 기존 언어모델에서 left-to-right를 통해 문장 전체를 predict하는 것과는 대조적으로, [MASK] token만을 predict하는 pre-training task를 수행한다.
- 이 [MASK] token은 pre-training에만 사용되고 fine-tuning에는 사용되지 않는다.
Task #2. Next Sentence Prediction (NSP)

두 문장을 pre-training 시에 같이 넣어줘서 두 문장이 이어지는 문장인지 or 아닌지를 맞춘다. 50%는 실제로 이어지는 문장(IsNext), 50%는 랜덤하게 추출된 문장(NotNext)를 넣어줘서 BERT가 예측하도록 한다.

Why?

QA(Question Answering)이나 NLI(Natural Language Inference) 같이 많은 downstream task는 두 문장 사이에 관계를 이해하는 것이 중요하다. 그래서 이를 위해서 BERT에서는 binarized NSP task를 수행한다.

- pre-training 후, task는 97% ~ 98% accuracy를 달성함. QA나 NLI에도 의미있는 성능 향상을 이뤄냄.
Pre-training data

BERT_english는 BookCourpus(800M words)와 English Wikipedia (2,500 words)를 사용했다. Wikipedia에서는 리스트, 표, 헤더를 제외한 텍스트 문단들만 추출하였다.

### 3.2 Fine-tuning BERT

sequence-level classification tasks의 경우, fine-tuning이 단순하다. task마다 task-specific input과 output을 BERT에 연결하고 모든 parameters를 fine-tuning한다.

- pre-training에 비해 fine-tuning은 훨씬 빠르다.
# 4. Experiments

11 NLP task에서의 BERT fine-tuning 결과이다.

### 4.1 GLUE

The General Language Understanding Evaluation benchmarck (Wang et al., 2018)

- 강건하고 범용적인 자연어 이해 시스템의 개발이라는 목적을 가지고 제작된 데이터셋. GLUE 내 9개의 task에 각각 점수를 매겨 최종 성능 점수를 계산함.
- 32 batch size, 3 epochs, learing rate=5e-5~2e-5으로 fine-tuning
- BERT_large가 BERT_base에 비해 성능이 뛰어나다.
### 4.2 SQuAD v1.1

The Standford Question Answering Dataset(SQuAD v1.1)

- 질문과 문단이 주어지고 그 중 substring인 정답을 맞추는 task. 정확한 답이 주어진 context 내에 존재할 것이라 가정함.
- 32 batch size, 3 epochs, learing reate=5e-5로 fine-tuning
- BERT_large는 기존 모든 시스템을 wide margin을 두고 최고 성능을 달성한다.
### 4.3 SQuAD v2.0

- 기존 데이터셋(SQuAD 1.1)에 새로운 5만 개 이상의 응답 불가능한 질문을 병합
- 단순히 정답이 가능할 때만 리턴하는 것이 아니라 주어진 본문에 정답이 없는 경우도 그 여부를 리턴하는 것이 좀더 어려워짐
- 48 batch size, 2 epochs, learning rate=5e-5로 fine-tuning
- BERT는 이전보다 +5.1 F1 향상을 이뤄냈다
### 4.4 SWAG

The Situations With Adversarial Generations dataset

일반적인 상식 추론을 측정하기 위해 사용되는 데이터셋

- 4개의 input sequences로 구성되며 각각은 given sentence(sentence A)와 가능한 continuation(sentence B)를 이은 것이다.
- 16 batch size, 3 epochs, learning rate=2e-5로 fine-tuning
- BERT는 SWAG task에 대해 SOTA를 달성한다.
# ⭐ 5. Ablation Studies ⭐

: 제안한 요소가 모델에 어떠한 영향을 미치는지 확인하고 싶을 때, 이 요소(feature)를 포함한 모델과 포함하지 않은 모델을 비교하는 것이다. 이를 통해, 시스템의 인과 관계(causality)를 간단히 확인 가능.

### 5.1 Effect of Pre-training Tasks

3.1 Pre-training BERT에서 소개한 MLM과 NSP task를 하나씩 제거하면서 각각 task의 영향력를 알아보자. BERT_base와 동일한 hyperparameter로 실험을 진행하지만 ablation한 2가지 다른 모델로 실험을 진행한다.

- No NSP : NSP를 없앤 모델
- LTR & No NSP : MLM 대신 LTR을 사용하고 NSP를 없앤 모델. OpenAI GPT 모델과 완전히 동일하지만 더 많은 training data를 사용함
- No NSP를 제거하면 QNLI, MNLI, SQuAD 성능 저하가 두드러진다
- LTR 모델의 성능은 MLM 모델보다 낮다. (MRPC와 SQuAD에서 큰 차이) BiLSTM을 붙여도, MLM 보다 성능이 하락하는 것을 보아 MLM task가 더 Deep Bidirectional함을 알 수 있다.
