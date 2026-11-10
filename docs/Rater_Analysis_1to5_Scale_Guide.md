# Rater Analysis Guide — 1–5 Attractiveness Scale

## Purpose of This Document

This guide explains every statistical measure used in the Rater Analysis and Dataset Comparison tools. It is written for readers who do not have a background in statistics. Each metric is explained in plain language — what it measures, what it tells you about the data, where it can mislead you, and what it cannot tell you on its own. The goal is to give you enough understanding to interpret findings confidently and explain them to others.

---

## Background: What We Are Measuring

The bundled `Demo_faces` dataset (a small set of AI-generated sample images) is there so you can try the app immediately, but it's too small to meaningfully illustrate most of the statistics below. Instead, this guide illustrates each metric using a real past run of the tool, on a much larger dataset — everything described here applies the same way regardless of dataset size, so the same reading applies whether you have 8 faces or 8,000.

In that run, sixty raters each looked at 2,750 face photographs (from the public SCUT-FBP5500 dataset) and assigned each face a score from 1 to 5:

| Score | Label |
|-------|-------|
| 5 | Very Attractive |
| 4 | Attractive |
| 3 | Average |
| 2 | Below Average |
| 1 | Unattractive |

The dataset is split into two groups: 2,000 Asian Female faces (AF_faces) and 750 Caucasian Female faces (CF_faces). Every rater scored every face independently, without seeing what others thought.

This produces a rich dataset but also a complex one. People perceive attractiveness differently. Some raters are generous, others harsh. Some use the full scale; others avoid the extremes. The statistics below help us understand both the individual raters and whether any meaningful patterns exist across the group.

---

## Section 1: Per-Rater Metrics

### N — Number of Faces Rated

**What it is:** The total count of faces this rater scored.

**What it tells us:** In a complete dataset, every rater should have rated all faces — 2,000 for AF or 750 for CF. If N is lower, some ratings are missing.

**How it could mislead:** If N varies significantly between raters, all other statistics for the low-N rater are less reliable. A rater who only scored 500 of 2,000 faces has statistics that may not represent how they would have rated the full set. Any comparison between raters with very different N values should be treated cautiously.

**What it does not capture:** It does not tell you *which* faces were rated, whether there was a pattern to what was skipped, or how long the rater took. A rater who rushed through 2,000 faces in ten minutes produces an N of 2,000 but the quality of thought behind each rating is unknown.

---

### Mean — Average Rating

**What it is:** Add up all of a rater's scores and divide by the number of faces they rated. The result is a single number between 1.0 and 5.0.

**What it tells us:** The mean captures the rater's overall generosity or harshness. A mean of 3.5 means, on average, this rater thought most faces were above average. A mean of 2.3 means they found most faces below average. It is the simplest summary of a rater's general tendency.

Comparing means across raters immediately shows the range of opinion. If rater A has a mean of 3.8 and rater B has a mean of 2.1, they are looking at the same set of faces and arriving at fundamentally different overall assessments. This could reflect genuine differences in their personal standards of attractiveness, cultural background, own-ethnicity bias, or simply how they interpreted the scale.

**How it could mislead:** The mean collapses the entire distribution of ratings into a single number and loses all shape information. Two raters can have identical means but completely different rating patterns. For example:

- Rater X: 40% at bucket 3, 30% at bucket 4, 30% at bucket 2 — mean ≈ 3.0
- Rater Y: 50% at bucket 5, 50% at bucket 1 — mean ≈ 3.0

Both have a mean of 3.0, but Rater X is a moderate, balanced rater while Rater Y is an extreme polariser. The mean alone would suggest they are identical — they are not. Always read the mean alongside the standard deviation and distribution chart.

**What it does not capture:** The mean does not tell you whether the rater is accurate, whether they agreed with the group, or whether there is systematic bias toward one ethnic group. A high mean might mean the rater is generous, or it might mean the faces they were shown genuinely skew attractive. Context matters.

---

### Std — Standard Deviation

**What it is:** A measure of how spread out a rater's ratings are around their mean. Technically, it is the square root of the average squared distance of each rating from the mean.

Think of it this way: if a rater gave every face exactly a 3, their std would be 0 — no variation at all. If they gave half the faces a 1 and half a 5, their std would be near 2 — maximum variation. Most raters fall somewhere in between.

**What it tells us:** Standard deviation captures how *decisive* or *discriminating* a rater is. A high std (above 1.2 in a 1–5 scale) means the rater makes strong distinctions between faces — some get very high scores, some get very low scores. A low std (below 0.7) means the rater clusters scores together, not differentiating much between faces.

In attractiveness research, a rater with very low std is less informative — if almost everything is a 3, there is little signal about which faces are more or less attractive. A rater with moderate to high std is more useful for ranking purposes because their scores spread across the scale.

**How it could mislead:** Standard deviation does not tell you *where* the spread is. A rater who gives mostly 2s and 4s has the same std as one who gives mostly 1s and 5s, but these are very different raters. The first is a moderate discriminator; the second is a polariser. Additionally, std does not tell you whether the spread is meaningful or random — a rater who assigned scores randomly to faces would produce a high std without any signal.

High std can sometimes indicate a rater who was inconsistent or distracted rather than genuinely discriminating. It should always be read alongside the Corr (correlation with consensus) metric: high std plus high corr suggests a genuine discriminator; high std plus low corr suggests the spread may be idiosyncratic or noise.

**What it does not capture:** Std does not capture the direction of spread (whether the rater leans high or low), the shape of the distribution (whether it is bell-shaped or U-shaped), or whether the spread reflects true perceived differences or arbitrary variation.

---

### Distribution Bar Chart

**What it is:** A visual representation of how many of a rater's ratings fell in each of the five buckets. The five bars (from left: 5, 4, 3, 2, 1) show the percentage in each bucket. Each bar is scaled relative to that rater's own tallest bar, so within a single rater's chart, the tallest bar always fills the space.

**What it tells us:** This is the most direct and unambiguous way to understand a rater's behaviour. It immediately reveals patterns that a single number cannot: whether the rater avoided extremes, whether they concentrated ratings in the middle, whether they show a clear preference direction. Two raters with the same mean and std can look completely different in their distribution chart.

**How it could mislead:** Because each bar is scaled relative to the rater's own maximum (not a fixed scale), you cannot directly compare bar heights across different raters. Rater A's bar at 30% and Rater B's bar at 30% will look the same height even if those 30%s mean different things in the context of each rater's overall spread. For cross-rater comparisons, use the Rater × Bucket Heatmap, which uses consistent percentage-based colouring.

**What it does not capture:** The chart shows the overall pattern but not the *ordering* of which faces received which scores. A rater could show an identical distribution chart to another while having completely disagreed about which specific faces are attractive.

---

### Shape

**What it is:** A plain-English label summarising the rater's overall rating tendency, based on their mean and standard deviation together.

| Shape | Meaning |
|-------|---------|
| Rates most faces highly | High mean (above 3.5), low std — consistently and predictably generous across all faces |
| Rates faces above average | Moderately high mean — a slight generous lean |
| Spread across all ratings | Balanced mean (around 3.0) with moderate spread — uses the full scale without a clear lean |
| Rates nearly everyone the same | Low std — gives very similar scores to most faces regardless of their actual attractiveness |
| Loves or hates — rarely in between | High std — makes strong distinctions, rarely landing in the middle of the scale |
| Rates faces below average | Moderately low mean — a slight harsh lean |
| Rates most faces poorly | Low mean (below 2.5), low std — consistently and predictably harsh |

**What it tells us:** Shape provides a quick, readable classification of rater style. It is particularly useful when scanning a table of 60 raters to identify groups of similar raters, or to flag outliers. A rater labelled "Rates nearly everyone the same" is contributing less signal to any research conclusion based on ranking, because their ratings barely differentiate between faces.

**How it could mislead:** The shape label is a coarse simplification. The thresholds that separate "Rates faces above average" from "Spread across all ratings" are chosen empirically, not mathematically derived. Two raters just either side of a threshold will receive different labels but may be nearly identical in practice. Shape should be used as a starting point for investigation, not as a definitive classification.

The Shape label is also based only on mean and std, so it cannot capture distribution *shape* — a U-shaped rater (who concentrates ratings at 1 and 5) could receive the "Loves or hates" label, while a rater with the same std but a bell-shaped distribution would receive a different label. Always read Shape alongside Curve.

**What it does not capture:** Whether the rater agrees with the consensus, whether they show ethnic bias, or whether their ratings are consistent with their other ratings in a logical way.

---

### Curve

**What it is:** A description of the *shape* of the rater's rating distribution — independent of where it is centred. Determined directly from the percentage of ratings in each bucket.

| Curve | What it means | Technical criterion |
|-------|---------------|---------------------|
| Bell-shaped | Most ratings cluster around bucket 3, tapering on both sides. The rater treats most faces as average and uses 1, 2, 4, and 5 less frequently. | Bucket 3 holds more than 40% of all ratings |
| Skews high | Most ratings are in the upper half of the scale (4 and 5). The rater generally finds faces attractive. | Buckets 4+5 hold more than 45%, or the single most-used bucket is 4 or 5 |
| Skews low | Most ratings are in the lower half of the scale (1 and 2). The rater generally finds faces unattractive. | Buckets 1+2 hold more than 45%, or the single most-used bucket is 1 or 2 |
| U-shaped | Ratings are concentrated at both extremes (1 and 5) with few in the middle. The rater makes very decisive all-or-nothing assessments. | Buckets 1+5 combined hold more than 40% and bucket 3 holds less than 20% |
| Spread out | Ratings are distributed relatively evenly across all five buckets without a clear peak or pattern. | None of the above criteria are met |

**An important note on methodology:** Curve is deliberately calculated from raw bucket percentages rather than from statistical skewness. Statistical skewness is a mathematical formula that can give misleading results on a five-point scale — for example, a rater who places 70% of their ratings at bucket 3 will appear mathematically "skewed" simply because bucket 4 receives slightly more ratings than bucket 2. What the eye clearly reads as a bell-shaped distribution, the skewness formula labels incorrectly. Using direct bucket percentages avoids this problem entirely.

**What it tells us:** Curve is the complement to Shape. Shape tells you *where* a rater centres their ratings; Curve tells you *how* they distribute around that centre. A rater with Shape "Rates faces above average" and Curve "Bell-shaped" is someone who gives most faces a 3 or 4 — moderate and well-distributed. A rater with the same Shape but Curve "Skews high" concentrates ratings at 4 and 5 — more decisive and polarised toward the high end.

Understanding Curve is important when interpreting consensus data. If most raters are Bell-shaped, the consensus will naturally produce many faces rated near 3. If many raters are U-shaped, the consensus may also look U-shaped, even if no individual face is genuinely controversial — it may simply reflect widespread polariser tendencies.

**How it could mislead:** Curve thresholds are practical cutoffs, not statistically principled boundaries. A rater with 39% of ratings at bucket 3 will be labelled "Spread out" while a rater with 41% will be "Bell-shaped," even though they are nearly identical. Use Curve as a guide, not a hard category.

Curve also cannot tell you whether a U-shaped distribution reflects a genuine, deliberate aesthetic judgment (this person truly sees faces as only beautiful or ugly, nothing in between) or a biased use of the scale (perhaps they gave 1s to faces they found culturally unfamiliar and 5s to faces from their own background).

**What it does not capture:** The Curve label does not encode which specific faces drove the shape. Two Bell-shaped raters could have opposite views on every individual face — they agree on the *pattern* but not the *content*.

---

### Extremes % — Percentage of Ratings at Bucket 1 or 5

**What it is:** The percentage of a rater's total ratings that landed at the two endpoints of the scale — bucket 1 (Unattractive) or bucket 5 (Very Attractive) — combined.

**What it tells us:** Extremes% captures polarisation in its purest form. A rater with high Extremes% (say 50%) is spending half their time making the strongest possible judgments — this face is very attractive, or this face is unattractive. They are not hedging. This is a more specific measure than standard deviation.

Extremes% is particularly useful when read alongside std. Two raters can have similar std values but very different Extremes%:

- Rater A: std = 1.1, Extremes% = 15% — spread comes from using buckets 2 and 4
- Rater B: std = 1.1, Extremes% = 55% — spread comes from using buckets 1 and 5

These raters have the same numerical spread but fundamentally different rating styles. Rater B is a true polariser; Rater A is a discriminator who avoids the extremes.

In a research context, high Extremes% raters are interesting subjects in themselves — they may have more defined or decisive aesthetic preferences, or they may be less calibrated to the middle range of the scale.

**How it could mislead:** A high Extremes% does not mean the rater is correct or that their strong opinions are shared by others. A rater could give 1s and 5s freely and still have a very low correlation with the consensus — their extremes may be idiosyncratic. Always read Extremes% alongside Corr to distinguish between "decisive and accurate" and "decisive but disagreeing."

Additionally, a low Extremes% does not necessarily mean the rater is thoughtful or balanced. They may simply be avoiding the extremes out of habit or discomfort with strong judgments, compressing all their ratings into the 2–4 range.

**What it does not capture:** The ratio of 1s to 5s. A rater with 50% Extremes% might give 40% fives and 10% ones (a harsh polariser toward high scores) or 25% of each. The Extremes% alone cannot tell you the direction.

---

### Corr — Pearson Correlation with Consensus

**What it is:** A number between −1.0 and +1.0 that measures how closely this rater's ratings match the consensus rating for each face. The consensus for each face is the average rating it received across all 60 raters. Pearson correlation specifically measures whether, as the consensus rating for a face goes up, this rater's rating also tends to go up — and by how much.

To understand correlation intuitively: imagine plotting one dot for every face on a graph, where the X position is the consensus rating and the Y position is this rater's rating. If all the dots form a perfect diagonal line (consensus 5 → rater 5, consensus 1 → rater 1), the correlation is 1.0. If the dots are a random cloud, the correlation is near 0. If they form a reverse diagonal (consensus 5 → rater 1), the correlation is −1.0.

| Correlation range | Interpretation |
|------------------|----------------|
| 0.85 – 1.0 | Very strong agreement. This rater largely shares the group's view of which faces are attractive. |
| 0.65 – 0.85 | Moderate agreement. Broadly aligned but with meaningful individual differences. |
| 0.40 – 0.65 | Weak agreement. This rater sees attractiveness noticeably differently from the group. |
| Below 0.40 | Poor agreement. This rater's rankings diverge significantly from the consensus. |
| Negative | Very rare. Would mean the rater tends to highly rate faces the group rates poorly, and vice versa. |

**What it tells us:** Correlation is the single most important metric for assessing how well a rater's perception aligns with the collective judgment. A high-correlation rater is a good representative of the group consensus. A low-correlation rater either has idiosyncratic aesthetic preferences, is applying different cultural standards, or may have rated faces in a less considered way.

In research, if you are trying to build a reliable consensus rating for each face, you might weight high-correlation raters more heavily or exclude very low-correlation raters from the consensus calculation. Conversely, low-correlation raters are themselves interesting subjects — understanding *why* they diverge can reveal cultural or individual differences in attractiveness perception.

**How it could mislead:** Correlation measures the *direction* of agreement, not the *magnitude* of ratings. A rater who gives every face exactly one point more than the consensus (e.g., always rates a "3-consensus" face as a 4) would have a perfect correlation of 1.0, even though every single rating is off by one. This is why Bias and Agree% exist as separate metrics.

Correlation also does not reveal whether disagreement is random (noise) or systematic (the rater consistently disagrees on a particular type of face, such as faces from a different ethnic group). A correlation of 0.5 could reflect random disagreement distributed evenly across all faces, or it could reflect very strong agreement on most faces but extreme disagreement on a specific subset.

**What it does not capture:** Correlation does not tell you anything about face-level disagreement — which specific faces caused the biggest gaps. For that, see the Most Controversial Faces section.

---

### Agree % — Exact Agreement with Consensus

**What it is:** The percentage of faces where this rater's rating exactly matches the consensus bucket (the consensus mean rounded to the nearest whole number).

**What it tells us:** Agree% is a stricter and more literal measure of agreement than correlation. If the consensus for a face is 3.2 (rounded to 3) and the rater gave it a 3, that counts as agreement. If the rater gave it a 4, it does not — even if that difference is small.

Agree% gives you a concrete, practical sense of how often a rater would arrive at the same classification as the group. In a research context, if you are using the consensus to label faces for training a machine learning model, a rater with high Agree% would produce a dataset close to the consensus labels without correction.

**How it could mislead:** Agree% is very sensitive to the rounding of the consensus. A face with a consensus mean of 3.49 rounds to 3; a face with 3.51 rounds to 4. A rater who gave these faces both a 3 or both a 4 would get a different agreement outcome depending on which side of the threshold the consensus fell — even though the actual consensus values are nearly identical. This rounding artefact means small changes in a face's consensus mean can change many raters' Agree% scores at once.

Additionally, a rater who consistently rates one bucket higher than the consensus (e.g., always gives a 4 where the consensus says 3) will have a low Agree% but might be internally consistent and have high correlation. Agree% penalises systematic offset even when the rater is clearly perceiving the same ordinal ranking as the group.

**What it does not capture:** Like correlation, Agree% does not tell you which faces caused disagreements, or whether disagreements are random or patterned. A rater with 40% Agree% might be disagreeing broadly across all faces, or they might agree perfectly on 80% of faces and strongly disagree on 20%.

---

### Outlier % — Strong Disagreement with Consensus

**What it is:** The percentage of faces where this rater's rating differed from the consensus by two or more buckets. For example, if the consensus for a face is 4 (Attractive) and the rater gave it a 2 (Below Average) or lower, that is a 2+ bucket disagreement and counts as an outlier rating.

**What it tells us:** Outlier% isolates the cases where a rater is not just slightly off but significantly diverging from the group. A rater with 1% Outlier% occasionally makes surprising calls but is broadly consistent. A rater with 20% Outlier% is frequently making ratings that the rest of the group would consider very wrong.

Outlier% is useful for identifying faces that provoke strong disagreement — if many raters contribute to a face's Outlier% count, that face is genuinely controversial. It is also useful for flagging raters who may need to be treated as outlier raters in research contexts.

**How it could mislead:** Outlier% treats a 2-bucket difference (e.g., rating 3 instead of consensus 5) the same as a 3-bucket difference (rating 2 instead of consensus 5) or even a 4-bucket difference (rating 1 instead of consensus 5). It is a blunt instrument that does not distinguish between "quite wrong" and "spectacularly wrong."

It also conflates two very different scenarios: a rater who is generally noisy and occasionally lands far from the consensus by chance, and a rater who has a specific, consistent pattern of disagreeing on a particular type of face. Both could produce similar Outlier% values but for very different reasons.

**What it does not capture:** The direction of outlier ratings (whether the rater rates too high or too low relative to the consensus), which specific faces are causing the outliers, or whether the outlier ratings cluster around a particular attractiveness level, ethnicity, or facial feature.

---

### Bias — Average Deviation from Consensus

**What it is:** For each face, the difference is calculated between this rater's score and the consensus mean for that face. Bias is the average of all those differences. A positive bias means the rater consistently gave higher scores than the consensus; a negative bias means consistently lower.

For example: if a face has a consensus mean of 3.0 and the rater gave it a 4, the deviation is +1. If another face has a consensus mean of 4.0 and the rater gave it a 3, the deviation is −1. If these were the only two faces, the bias would be (1 + (−1)) / 2 = 0 — but this rater was off by 1 on every face, which would not be visible in the mean bias.

**What it tells us:** Bias reveals systematic offset. A rater with bias +0.5 is, on average, rating every face half a point above what the group thinks. This is important because a rater with high correlation and positive bias will tend to elevate the entire ranking — all their faces are rated a bit too high — even though their *ordering* of faces may be correct. This is sometimes called scale-use bias.

In research, understanding each rater's bias allows you to correct for it. If you are combining ratings from multiple raters into a consensus, knowing that rater A has bias +0.6 and rater B has bias −0.4 tells you they are using the scale very differently, and raw averaging will be affected by that discrepancy.

**How it could mislead:** Bias averages over all faces, which means opposing deviations cancel each other out. A rater who rates attractive faces much too high and unattractive faces much too low might have a bias of exactly 0 — they are not systematically lenient or harsh overall, but they are exaggerating in both directions. The mean bias would make them look perfectly calibrated when they are not. Always read Bias alongside std and Extremes% to get the full picture.

Bias also assumes that the consensus mean is the "correct" answer to compare against, which is a circular assumption — if most raters have positive bias, the consensus itself will be elevated, making it appear that fewer raters have bias when in fact the whole group is biased in the same direction.

**What it does not capture:** Bias does not tell you whether the offset is consistent across all types of faces (global bias) or concentrated on specific faces — for example, a rater might have zero bias overall but systematically rate faces of one ethnic group higher than the consensus and faces of another group lower, with the two biases cancelling out in the average.

---

## Section 2: Distribution Charts

### Consensus Face Distribution

**What it is:** A bar chart showing how many faces received each consensus rating (1–5) when all raters' scores for each face are averaged and rounded. This represents the overall difficulty and composition of the face dataset.

**What it tells us:** This is the single most important baseline for the entire dataset. It tells you whether the face set was representative of the general population, or curated for a specific purpose.

- A **bell-shaped** consensus distribution (most faces at 3, fewer at 2 and 4, fewest at 1 and 5) suggests the dataset reflects a normal spread of attractiveness, similar to what you might find in a random sample of faces from the general population.
- A **bimodal** (U-shaped) distribution (many faces at 1 and 5, few at 3) suggests the dataset was deliberately curated to include clearly attractive and clearly unattractive faces, excluding middle-ground faces. Results from such a dataset may not generalise to real-world applications where most faces are average.
- A distribution **skewed toward high scores** (most faces rated 4 or 5) suggests either a generous rater pool or a dataset selected to feature attractive people.
- A distribution **skewed toward low scores** suggests the opposite.

Understanding the consensus distribution is essential before interpreting any other finding. If a rater has a mean of 3.8, you cannot know whether that reflects generosity or the actual attractiveness of the faces without knowing the group consensus distribution.

**How it could mislead:** The consensus distribution reflects both the actual attractiveness distribution of the faces chosen and the collective biases of the 60 raters. If all 60 raters are from a cultural background that finds one ethnic group less attractive on average, the consensus will embed that cultural bias as if it were objective fact. The consensus is not ground truth — it is the central tendency of this particular group of raters.

The rounding process (averaging scores and rounding to the nearest integer) also compresses subtle differences. A face with a consensus mean of 2.51 and one with a mean of 3.49 will be assigned to different buckets despite being close in absolute terms.

**What it does not capture:** The consensus distribution does not show variance — how much raters disagreed about individual faces. Two datasets could have identical consensus distributions but very different levels of inter-rater agreement.

---

### Rater × Bucket Heatmap

**What it is:** A grid where every row is one rater and every column is one bucket (5 to 1, left to right). Each cell shows the percentage of that rater's ratings that fell in that bucket, using colour intensity: dark means rarely used, bright means frequently used.

**What it tells us:** This is the most efficient way to compare all 60 raters' distribution patterns simultaneously. At a glance you can see:

- Raters who barely ever use bucket 1 or 5 (very light cells in those columns)
- Raters who funnel almost everything into bucket 3 (very bright centre column)
- Raters with distinctive U-shaped patterns (bright cells at both ends, dark in the middle)
- Whether raters who share a "Shape" label actually show similar distributions visually

The heatmap also reveals structural features of the rater pool: if the entire column for bucket 5 is dark for nearly every rater, it suggests systematic under-use of the top category, which would compress the consensus and make it harder to distinguish the most attractive faces.

**How it could mislead:** The rows are sorted by Shape group and mean (the same order as the main table), which means raters with similar labels appear near each other. This can make the grouping look cleaner and more distinct than it actually is — a different sort order might reveal that the groups are less coherent. The heatmap also uses colour intensity rather than absolute size, so comparing percentages across rows requires caution: a moderately bright cell in one row might represent the same percentage as a slightly less bright cell in another row.

**What it does not capture:** The heatmap shows what percentage of ratings went where, but not which faces drove those ratings. Two raters with identical heatmap rows could have disagreed on every single face.

---

### Agreement with Consensus — Ranked Bar Chart

**What it is:** A bar chart with one bar per rater, sorted from highest to lowest Pearson correlation with the consensus. Bars are coloured by tier: green for strong agreement (corr ≥ 0.8), purple for moderate (0.5–0.8), and red for weak (below 0.5).

**What it tells us:** This chart immediately answers the question: "How aligned is this rater pool?" If most bars are green, the 60 raters broadly share a common view of which faces are attractive. If there are many red bars, there is significant divergence — the concept of a "consensus" may be less meaningful.

The shape of the ranked bar chart also matters. A gradual decline from high to low correlation suggests a continuous spectrum of agreement. A sharp drop after the first few raters suggests that most raters agree and a small minority diverges strongly.

In a research context, this chart supports decisions about which raters to include in a consensus calculation. Raters at the bottom of the chart are not necessarily "wrong" — they may represent a genuinely different cultural or individual perception of attractiveness — but their divergence from the majority is worth acknowledging.

**How it could mislead:** The chart uses the consensus as the reference point, but the consensus is itself shaped by all 60 raters. Low-correlation raters pull the consensus slightly toward themselves, which means a rater who is truly a strong outlier might appear to have a slightly higher correlation than they would if they were removed from the consensus. Conversely, if two raters have nearly identical non-consensus opinions, their mutual agreement is not visible here — this chart only shows agreement with the group average, not with each other.

**What it does not capture:** Why a rater disagrees with the consensus. Low correlation could reflect cultural differences, random noise, systematic bias toward one type of face, or deliberate application of a different aesthetic standard. This chart identifies who disagrees; other tools are needed to understand why.

---

### Rating Entropy per Rater

**What it is:** Shannon entropy is a measure from information theory that quantifies how evenly a rater distributes their ratings across all five buckets. It is expressed here as a percentage of the theoretical maximum, which would occur if each bucket received exactly 20% of the ratings.

For a practical understanding: imagine a rater who gives every face exactly a 3. All 2,000 ratings land in one bucket. There is zero uncertainty about what rating they will give next — it will be 3. This rater has zero entropy. Contrast this with a rater who is completely unpredictable and uses all five buckets equally. Maximum entropy.

Entropy in this context is essentially asking: "If you had to guess this rater's next rating before they gave it, how uncertain would you be?"

**What it tells us:** Entropy reveals whether a rater is truly using the full scale. This is important because standard deviation can be misleading. Consider:

- **Rater A:** 45% at bucket 3, 45% at bucket 1, 10% scattered — std is high, entropy is low (only two buckets dominate)
- **Rater B:** 25% in each of buckets 2, 3, 4, 5 and almost nothing at 1 — std is moderate, entropy is very high

Standard deviation would suggest Rater A is a more discriminating rater, but entropy reveals they are functionally using only two categories. Rater B's ratings carry more information because they distinguish between four levels.

In research, a rater with low entropy is contributing less statistical information per rating. Their scores can effectively be reduced to a binary or ternary system without much loss. High-entropy raters are getting more use out of the five-point scale.

**How it could mislead:** High entropy does not mean a rater's judgments are valid, consistent, or agreed upon by others. A rater who assigned scores randomly would achieve near-maximum entropy — each bucket used equally — but would have zero correlation with the consensus. Entropy measures breadth of scale use, not accuracy or reliability. Always pair entropy with correlation to distinguish between "broad and accurate" and "broad but random."

Low entropy also does not necessarily indicate a poor rater. A rater who genuinely believes most faces are average and uses bucket 3 frequently is being honest, not lazy. The low entropy reflects the rater's actual perception, not carelessness.

**What it does not capture:** Entropy treats all buckets as equally important. It does not distinguish between a rater who avoids the extremes (1 and 5) and one who avoids the middle (3). Both could have similar entropy values despite showing completely different patterns.

---

### Most Controversial Faces

**What it is:** The 20 faces from the dataset with the highest standard deviation of ratings across all 60 raters. For each face, the std tells you how much disagreement there was — a std of 1.5 on a 1–5 scale represents very strong disagreement, while a std of 0.3 represents near-consensus.

**What it tells us:** These faces are the most informationally valuable in the dataset for studying perceptual differences. When 60 raters strongly disagree about a face, it reveals that something about that face triggers inconsistent responses — perhaps it is ambiguous, crosses cultural aesthetic boundaries, or touches on features that are weighted very differently by different people.

Controversial faces can be analysed for common characteristics: Do they tend to be from one ethnic group? Do they share certain facial features (e.g., distinctive makeup, unusual facial geometry, non-standard lighting in the photograph)? Are the raters who strongly agree with each other about this face also agreeing with each other about other faces, or is this face specifically divisive?

These are among the most scientifically interesting data points in the dataset precisely because they reveal the edges of consensus and the boundaries of shared perception.

**How it could mislead:** High std on a face could reflect genuine aesthetic controversy or it could reflect photograph quality issues. A poorly lit, unusual-angle, or low-resolution photograph might receive variable ratings not because raters disagree on beauty but because they cannot clearly see the face. The dataset's photographic consistency should always be verified before concluding that disagreement is purely perceptual.

Additionally, "controversial" in this context means controversial among this particular group of 60 raters. The same face might be broadly agreed upon by a different cultural or demographic rater pool. Controversy is relative to the sample.

**What it does not capture:** The direction of the disagreement. A face with std of 1.5 might have half the raters giving it a 5 and half giving it a 1, or it might have ratings spread across all five buckets. Both produce the same std. The distribution bar chart under each thumbnail shows the actual shape of disagreement.

---

### Most Agreed-Upon Faces

**What it is:** The 20 faces with the lowest standard deviation of ratings — the faces where all 60 raters gave nearly the same score.

**What it tells us:** These faces represent the closest thing to objective consensus in the dataset. A face that every rater independently gives a 5 is, within the scope of this rater pool, very broadly considered attractive. A face universally rated 1 is very broadly considered unattractive.

These faces serve as calibration anchors — they are the benchmark against which rater reliability can be assessed. If a rater gives a face that 58 of 60 raters scored as a 5 a score of 1, that is a strong signal that something unusual is happening with that rater's judgment of that face.

They are also scientifically interesting in a different way from controversial faces: they represent faces that transcend individual aesthetic preferences, at least within this rater pool. Understanding what these faces have in common — and whether they share common features across the AF and CF datasets — could be a research finding in itself.

**How it could mislead:** Universal agreement does not mean universal attractiveness in an objective sense — it means universal agreement among this sample of raters. A different cultural sample might produce very different "universally agreed" faces. Findings from agreed-upon faces must be contextualised within the specific demographics of the 60 SCUT raters.

**What it does not capture:** Why the agreement occurred. Is a universally agreed-upon face objectively high-quality in some measurable way, or does it happen to trigger a shared cultural or instinctive response? This question cannot be answered by the rating data alone.

---

## Section 3: Dataset Comparison (AF vs CF)

### Mean — By Dataset

**What it is:** Each rater's mean rating calculated separately for the AF (Asian Female, n=2,000) and CF (Caucasian Female, n=750) faces.

**What it tells us:** Comparing these two means for a single rater shows whether they systematically rate one ethnic group of faces higher or lower than the other. This is a direct measure of potential own-ethnicity bias or cross-cultural aesthetic preference.

**How it could mislead:** The AF and CF face sets are not matched on any dimension other than ethnicity — they may differ in photography quality, age range, makeup, or actual attractiveness distribution. A difference in means between AF and CF ratings could therefore reflect genuine differences between the two face sets rather than rater bias. Before concluding that a difference in means reflects bias, the two face sets themselves need to be examined for systematic differences.

The CF dataset is also much smaller (750 faces) than the AF dataset (2,000 faces), which means CF means are based on fewer data points and therefore less stable. Small differences in CF means should be treated with more caution than the same difference in AF means.

**What it does not capture:** Whether any difference is consistent across all faces or driven by a small number of strongly-rated faces in one set.

---

### Diff (AF − CF)

**What it is:** The arithmetic difference between a rater's AF mean and their CF mean. Positive values mean the rater, on average, gave higher scores to Asian Female faces; negative values mean higher scores to Caucasian Female faces.

**What it tells us:** Diff is the simplest quantification of between-group rating bias. A diff of +0.5 means, on average, this rater rated AF faces half a point higher than CF faces — a meaningful difference on a 5-point scale.

Across the full table, the distribution of Diff values reveals whether the rater pool has systematic group-level bias. If most raters show a positive Diff, it may suggest the AF faces are genuinely more attractive on average, or it may reflect own-ethnicity bias if most raters are of Asian background, or it may reflect differences in the face sets themselves.

**How it could mislead:** As with the individual means, Diff is sensitive to differences between the AF and CF face sets. A difference in average attractiveness between the two sets would produce non-zero Diff values across all raters even in the complete absence of bias. The Diff should always be interpreted alongside the consensus distribution of each dataset separately.

A Diff near zero does not mean a rater has no bias — they might rate specific faces very differently but have the biases cancel out in the mean. Face-level analysis (looking at which specific faces drove disagreements) would be needed to detect this.

**What it does not capture:** Whether the difference is statistically significant given the sample sizes. A diff of 0.15 across 750 CF faces and 2,000 AF faces may or may not be statistically meaningful — formal significance testing would be needed to determine this.

---

### Bias Badge

**What it is:** A colour-coded label that summarises whether a rater systematically rated one ethnic group higher than the other, based on the Diff value:

| Badge | Colour | Meaning | Threshold |
|-------|--------|---------|-----------|
| Prefers AF | Indigo | Rated AF faces higher on average | Diff > +0.2 |
| Prefers CF | Teal | Rated CF faces higher on average | Diff < −0.2 |
| No preference | Grey | No meaningful systematic difference | −0.2 ≤ Diff ≤ +0.2 |

The threshold of ±0.2 is used to filter out trivial differences that are more likely to reflect natural variation in rating than genuine preference. The colour scheme uses indigo and teal deliberately — red and green are avoided because they would imply one group is "better" than the other, which is not what this badge measures.

**What it tells us:** The badge gives a quick visual summary for scanning across all 60 raters at once. It enables you to see at a glance whether most raters show the same preference direction (systematic group-level bias) or whether preferences are mixed (suggesting the difference may be driven by the face sets rather than rater bias).

**How it could mislead:** The ±0.2 threshold is a practical choice, not a statistically derived one. A rater with Diff = 0.19 and a rater with Diff = 0.21 receive different badges but are nearly identical. The badge should be used for pattern recognition across the whole table, not as a definitive classification of individual raters.

**What it does not capture:** The consistency of the preference. A rater might prefer AF faces on average but strongly prefer CF faces for a specific subset of the dataset. The badge cannot detect this kind of conditional preference.

---

## Section 4: Cross-Metric Interpretation

The greatest risk in using any of these statistics is interpreting each one in isolation. The following combinations are especially informative when read together:

### High Corr + Non-zero Bias
The rater shares the group's ordering of faces (they agree on which faces are more or less attractive relative to each other) but is consistently offset. They are a calibrated but systematically lenient or harsh rater. Their rankings are reliable; their absolute scores need adjustment.

### Low Corr + Low Outlier%
The rater broadly disagrees with the consensus but rarely makes extreme outlier calls. Their disagreement is diffuse — slightly off on most faces rather than spectacularly wrong on a few. This may reflect a consistently different aesthetic standard rather than random noise.

### High Std + Low Corr
The rater makes strong distinctions between faces but those distinctions do not align with the group. This is the profile of a genuinely idiosyncratic rater — they have a clear and decided view of attractiveness but it diverges from the consensus. These raters are the most interesting subjects for studying individual differences.

### High Std + High Corr
The rater makes strong distinctions and those distinctions align with the group. This is the profile of a highly discriminating, reliable rater — they are essentially an amplified version of the consensus, agreeing on the direction and order but with stronger opinions.

### Low Entropy + Low Std + High Corr
The rater concentrates their ratings in a narrow range but that range aligns with where the consensus sits. They are accurate but undifferentiating — they agree on which faces are better but their compressed scale use makes it hard to distinguish between faces of similar attractiveness.

### High Diff (AF − CF) + High Corr for both
A rater who is both reliable (agrees with consensus) and shows consistent between-group preference. This is the most robust evidence of a genuine preference direction, because the rater is not an outlier rater — their consensus alignment tells you their ratings are considered, not random.

---

## Section 5: Bucket Grouping Results — Views and Sort Options

The Bucket Grouping Results tab displays face images grouped into their assigned attractiveness buckets (1–5). It has three view modes and four sort options. Not all combinations are available, and understanding why is important for interpreting what you are looking at correctly.

### View Modes

**Mine** — Shows your own personal bucket assignments. You can click any face to move it to a different bucket. All sort options that are relevant to your data are available here.

**Consensus** — Shows the collective bucket assignment for each face, derived by finding the most common rating each face received across all raters. This is automatically generated from the data and cannot be manually edited. Clicking a face opens a preview of the image but does not allow any changes. The consensus represents the group's collective judgment — it should not be altered by any individual.

**Other** — Shows a specific rater's bucket assignments. Select a rater from the chips that appear. As with Consensus, you can click faces to preview them but cannot change their assignments. This view is purely for inspection.

### Sort Options

Faces within each bucket can be sorted in different ways. Not every sort option is available in every view — the table below explains the rules and the reasoning behind them.

| Sort Option | Mine | Consensus | Other | Notes |
|-------------|------|-----------|-------|-------|
| TrueSkill | Disabled | Disabled | Disabled | Requires pairwise comparison data from the Compare tab. No such data exists in this setup — the ranking faces folder is empty. |
| Bradley-Terry | Disabled | Disabled | Disabled | Same reason as TrueSkill. Both options are shown so users understand the feature exists but cannot be used without comparison data. |
| Group Average Rating | ✓ | ✓ | Disabled | Sorts faces by their mean rating across all 60 raters, highest first. Relevant for Mine (gives context of where your face sits relative to the group) and Consensus (the natural order for group-derived data). Disabled for Other because this metric reflects the group, not the individual rater being viewed — applying it would misrepresent what that rater actually did. |
| Manual Ranking | ✓ (if saved) | Disabled | Disabled | Uses your personally saved drag-and-drop ranking from the Ranked Grouping tab. Only enabled in Mine view, and only if you have actually created and saved a manual ranking. Disabled for Consensus because your personal ranking has no bearing on group-derived data. Disabled for Other because it is your ranking, not the rater being viewed. |

### Why These Restrictions Matter for Research

The restrictions on sort options are not arbitrary — they prevent a subtle but important error in interpretation.

**Group Average Rating in Other view:** If you are examining rater 004's bucket assignments and sort by Group Average Rating, you are imposing the group's ordering onto that rater's personal view. The faces would appear ordered by group consensus, not by anything rater 004 did. This creates a misleading picture — it looks as though rater 004's categories are ordered by group attractiveness when they are simply displayed that way. The sort should always reflect the perspective you are examining.

**Manual Ranking in Consensus view:** Your manual ranking is a personal artifact — it records your own drag-and-drop ordering of faces. Applying it to the consensus view would sort a group outcome by one person's personal ranking, which has no relationship to how the group categorised anything. It would look like the consensus data is ordered meaningfully when it is actually ordered by an unrelated personal judgment.

**Why TrueSkill and Bradley-Terry remain visible when disabled:** These are powerful and well-established ranking models that are fully implemented in the tool. They require pairwise comparison data (generated when users compare pairs of faces in the Compare tab). In the current setup the comparison face folder is empty, so no such data exists. The buttons are shown in a disabled state rather than hidden so that users understand the capability is available — if comparison data were to be generated in future, these options would become active automatically.

### Previewing Faces

All face thumbnails are clickable in every view mode. Clicking a face opens a larger preview showing the image at full panel width, which is important since the thumbnails in the grid are small and individual facial features are difficult to assess at that size.

- In **Mine** view, the popup shows the face with category buttons, allowing you to reassign it to a different bucket.
- In **Consensus** or **Other** view, the popup shows the face in preview-only mode with a Close button and no category options. The title changes from "Re-categorise" to "Preview" to make this distinction clear.

---

## Section 6: General Cautions for Research Use

**The consensus is not ground truth.** The consensus is the average of 60 specific people's opinions. It reflects their collective biases, cultural backgrounds, and interpretations of the scale. It should be presented as "the central tendency of this rater pool" rather than as an objective measure of attractiveness.

**Sample size matters for all statistics.** Statistics based on fewer faces (particularly CF with 750 faces) are less stable. Differences that appear meaningful in a small sample may not replicate.

**These statistics describe behaviour, not intent.** A rater who shows high Diff (preferring AF faces) may be expressing genuine aesthetic preference, may be from an ethnic background that shares features with the AF faces, may be responding to photographic differences between the datasets, or may be exhibiting bias in the psychological sense. These statistics identify the pattern; they cannot explain the cause.

**Multiple comparisons.** When looking at 60 raters across many metrics, some patterns will appear by chance. Findings should be treated as exploratory rather than confirmatory unless a specific hypothesis was defined before the analysis.

**The scale is ordinal, not interval.** There is no guarantee that the difference between a 1 and a 2 feels the same to a rater as the difference between a 4 and a 5. Statistical tools that assume equal intervals (like mean and Pearson correlation) should be used with this limitation in mind.
