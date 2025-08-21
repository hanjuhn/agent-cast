# [NLP 학습] 3주차 : LoRA / 논문 리뷰 : LoRA: Low-Rank Adaptation of Large Language Models

**페이지 ID:** 255d3416-0518-80ff-acf3-d7b17f884b8b
**생성일:** 2025-08-20T08:03:00.000Z
**마지막 수정:** 2025-08-20T08:03:00.000Z
**URL:** https://www.notion.so/NLP-3-LoRA-LoRA-Low-Rank-Adaptation-of-Large-Language-Models-255d3416051880ffacf3d7b17f884b8b

---

이전 포스트에서 다룬 언어모델에 대한 이해를 바탕으로 LoRA에 대해 학습해본다. LoRA와 관련된 논문 "LoRA: Low-Rank Adaptation of Large Language Models"를 리뷰한다.

1. LoRA

2. 논문 리뷰

### 1. LoRA

- Microsoft Research에서 2021년 발표한 "LoRA: Low-Rank Adaptation of Large Language Models" 논문에서 제안된 모델
- LLM을 더 효율적으로 tuning하기 위한 기술로 주목을 받음
1) LoRA 등장 배경

- NLP에선 대규모 언어모델을 각각의 task에 맞게 fine-tuning하는 것이 일반적이었음 pre-training 과정에서 어느정도 최적화된 파라미터를 각 task에 맞게 조정pre-train 모델의 크기가 커지면서 파라미터 전체를 fine-tuning하는 것에 많은 시간과 리소스가 소요대규모 언어모델의 fine-tuning을 더 효율적으로 할 수 있는 방법의 필요성
➡️

2) LoRA의 원리

- W_0 (d*k) : pre-trained weight matrix, 사전학습 가중치 행렬
- A (r*k), B (d*r) : rank decomposition matrices, 저차원 행렬
- ΔW = B*A : ΔW_0를 저차원에서 근사, 업데이트 값
- r : LoRA rank, r << min(d, k)
→ A는 random gaussian initialization으로, B는 0으로 초기화

행렬 A, B는 nn.linear layer 형태로 dense layers 뒤에 단순히 더해짐

→ W_0 값은 고정한 채로 ΔW_0를 근사하는 저차원 행렬 BA를 학습

→ ΔW = B*A값이 W_0에 더해지며 W_0가 간접적으로 업데이트 됨

=> ΔW = B*A는 결국 W_0 중에서 task별로 중요하게 사용되는 일부 파라미터에 대해 학습

=> pre-trained 모델의 전체 weight matrix를 업데이트하지 않고

더 적은 수의 중요한 파라미터만 사용하는 rank decomposition matrices를 학습함으로써

pre-trained LLM을 downstream task에 더 효율적으로 tuning

출처 : https://velog.io/@d4r6j/PEFT-Parameter-Efficient-Fine-Tuning

### 2. 논문 리뷰

논문명 : LoRA: Low-Rank Adaptation of Large Language Models

저자명 : Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, Weizhu Chen

https://arxiv.org/abs/2106.09685

LoRA: Low-Rank Adaptation of Large Language Models
An important paradigm of natural language processing consists of large-scale pre-training on general domain data and adaptation to particular tasks or domains. As we pre-train larger models, full fine-tuning, which retrains all model parameters, becomes le
arxiv.org

✏️ 논문 내용 정리

▶ 0. Abstract

- 자연어 처리의 중요한 패러다임은 large-scale pre-training 모델을 특정 tasks로 adaptation하는 것
- pre-train 모델의 규모가 커짐에 따라 모든 모델 파라미터를 재학습하는 full fine-tuning 방식은 점점 현실적이지 못하게 됨
- LoRA 또는 Low-Rank Adaptation을 제안
= freezes the pre-trained model weights

+ injects trainable rank decomposition matrices into each layer of the Transformer architecture

=> downstream tasks를 위해 훈련해야할 파라미터의 수를 크게 감소시키는 학습 방식

- Adam으로 미세 조정된 GPT-3 175B에 비해 LoRA는 훈련하는 파라미터의 수를 10,000배, GPU 메모리 요구 사항을 3배 줄일 수 있었음
- 또한 LoRA는 훈련하는 파라미터가 적고 추가적인 inference latency이 없음
- RobERTA, DeBERTA, GPT-2 및 GPT-3 pre-trained 모델의 성능을 향상시킴
▶ 1. Introduction

1) 기존 fine-tuning의 문제

- 대부분의 NLP에서 사전학습된 대규모 언어모델에 대하여 모든 파라미터를 fine-tuning해 downstream task에 adapt하는 방식
- 이러한 fine-tuning은 새로운 모델이 원래 모델만큼 많은 파라미터를 학습해야한다는 단점
2) Low-Rank Adaptation (LoRA) approach

- model adaptaion 과정에서 change in weights에도 low instrinsic rank가 있다고 가정
- pretrained weights는 고정한 채로, weights' change in dense layers의 rank decomposition matrices를 최적화함으로써 기존의 dense layers를 간접적으로 훈련
- deep layers를 직접적으로 학습하는 것이 아닌, weights' change의 low-rank matrices을 optimize
- rank decomposition matrices = low-rank matrices
- 동일한 사전학습된 모델에 대해서도 low-rank matrices A, B를 다르게 둠으로써 다양한 작업에서 LoRA 모듈들을 구축할 수 있음
- 대부분의 파라미터에 대해 gradient를 계산하거나 optimizer state를 유지할 필요가 없어 훈련을 더 효율적으로 만들고 하드웨어도 적게 사용
- 간단한 linear 연산으로 trainable matrices와 frozen weights를 병합하기 때문에 inference latency가 도입되지 않음
- 기존의 다른 모델들과 함께 사용될 수 있음
* inference latency

▶ 2. Problem Statement

- LoRA는 objective에 관계없이 사용 가능함
- 논문에서는 language modeling task에 대해 집중
- 주어진 task-specific prompt에 대하여 정답의 conditional probabilities를 최대화하는 task
- P_Φ(y∣x) : 파라미터가 Φ인, Transformer 구조의 사전학습 언어모델
- Z = {(x_i, y_i)} (i=1,..,N) : Context-Target Pairs의 훈련 데이터셋
- P_Φ(y∣x)를 downstream conditional task generation task에 적용
① Full Fine-tuning

- 모델은 pre-trained weights인 Φ_0로 초기화되고, backpropagation 과정에서 Φ_0 +ΔΦ로 업데이트
- |ΔΦ| = |Φ_0|, 전체 파라미터를 gradient를 사용해 모두 업데이트
- 각각의 downstream task마다 |Φ_0| 크기의 파라미터를 업데이트 해야함
- pre-trained weights |Φ_0| 크기가 커질수록 fine-tuning에 더 많은 연산이 요구
② LoRA approach

- Θ : LoRA 파라미터
- |ΔΦ| = |ΔΦ(Θ)|, |Φ_0| >> |Θ| (|Φ_0|의 0.01% 정도)
- 모든 pre-trained weights Φ_0에 대해서 업데이트 하는 것이 아니라,
downstream task-specific increment ΔΦ(Θ)만큼에 대해서만 업데이트

- LoRA를 이용해 backpropagation에서 파라미터의 일부만 업데이트
▶ 3. Aren't Existing Solutions Good Enough?

- model adaptation에서 파라미터 및 계산의 효율성을 증진하기 위한 시도는 이전부터 존재해왔음
- 크게 2가지 접근 방식이 존재하나 각각 한계점을 가지고 있음
①  adding adapter layers → Adapter Layers Introduce Inference Latency

- transformer block에 adapter layer를 추가하여, fine-tuning 대신 adapter layer만 학습시키는 방식
- adapter layers에서 추가적인 연산 발생하는데, LNN은 adatper layer에서의 연산을 순차적으로 처리해야하기 때문에 연산 시간이 매우 증가함
② optimizing input layer activations → Directly Optimizing the Prompt is Hard

- language model의 입력으로 들어가는 input embedding에 prompt embedding을 추가하여, fine-tuning 대신 prompt embedding을 다양한 학습 방법으로 학습시키는 방식
- 대표적인 예시가 prefix tuning인데, 최적화가 어렵고 성능이 단조적으로 증가하지도 않음
- downstream task로 tuning하는데 사용할 수 있는 sequence의 길이가 감소하는 문제도 존재
▶ 4.Our Method

- LoRA는 딥러닝 모델의 모든 dense layers에 사용가능함 이 논문에서는 Transformer Language Models에 대해 집중
▶ 4.1 Low-Rank-Parametrized Update Matrices

- NN은 행렬곱을 수행하는 많은 dense layers를 가지고 있는데, 이 layers의 weight matrices는 full-rank 사전학습된 언어모델은 임의의 더 작은 subspace로 전사되어도 효과적으로 학습될 수 있는 low instrisic dimension을 가지고 있음따라서 사전학습된 언어모델을 downstream task로 adaptation할 때, weights' update도 low instrisic dimension을 가질 것이라고 가정
- W_0 (d*k) : pre-trained weight matrix
- B (d∗r) / A (r∗k) : trainable rank decomposition matricesA = Random Gaussaian, B = 0 으로 초기화 → ΔW=BA=0로 초기화
- ΔW = B*A : A와 B로 계산되는 trainable 파라미터의 업데이트 값
- r : LoRA rank, r << min(d,k)
- pre-trained 모델의 weight matrix는 고정한 상태에서

- LoRA에서 업데이트의 특징
- A Generalization of Full Fine-tuning: LoRA rank r을 원래 pre-trained weight matrices의 rank로 설정하면 full fine-tuning과 동일한 학습으로 수렴
- No Additional Inference Latency: 모델을 다른 task로 전환할 때, B*A를 빼서 W_0를 얻고, W_0에 새로운 B'*A'를 바로 더해주면 되기 때문에 inference latency가 추가되지 않음
