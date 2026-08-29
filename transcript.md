# TikTok TechJam 2026 — Track 4: Shopping Copilot (AI Conversational Search and Recommendations)

Technical workshop webinar · Fri 28 Aug 2026, 4:00pm SGT · 56m 09s
Speakers: Phyllis Chua (APAC Early Careers, host) · Chenxin Liu (Search Algorithm Engineer, Global E-Commerce Search)

> Auto-transcribed and lightly hand-corrected against the slides. Timestamps are accurate to the recording; occasional wording may not be verbatim.

---

**[00:02]** Hi, everyone, and welcome back. We're now on our fourth webinar for the day for TikTok TechJam 2026 Technical Workshop series, where we will be diving into track four, Shopping Copilot, AI conversational search, and recommendations. Before we begin, I'm Phyllis, and I'm very, very glad to be here today, and I'm part of the APAC Early Careers team here at TikTok. So nice to meet everyone. So I've been with the team for more than four and a half years now, and I manage regional university relations and campus engagements in Southeast Asia and Japan.

**[00:31]** I'm also the project manager of TikTok TechJam 2026, and I'm very, very excited to have you join us today at this webinar, which we have prepared to help you better understand Track 4. So I would first provide a quick overview of this hackathon, and then I'll pass the mic to Chenxin, our engineer who built Track 4 to actually deep dive into this problem statement. So Chenxin will be sharing valuable insights on this track to help you really better prepare for success, and hopefully, you know, you're having a great time to conquer this problem statement.

**[01:03]** Now we will then conclude this session with live Q&A where you can actually type your questions in our chat box. So TikTok TechJam is our annual flagship student hackathon and we're guided by our hackathon mission, which is to build with joy and code for change. Now, build with joy is a celebration of learning, collaboration and curiosity. So this is in line with TikTok's mission to inspire creativity and bring joy. So participants are encouraged to embrace the spirit of innovation. You are encouraged to really experiment freely,

**[01:33]** be bored and try with new ideas, support each other, and also have fun along the way as you grow together as builders of the future. Now, code for change challenges participants to think beyond the code and to focus on impact. We hope that through this hackathon, you're empowered to build solutions that actually drive positive change, solve real-world business problems, and also reflect TikTok's belief in shaping the future with responsible technology. Now, this year, you can fly solo or participate in teams of up to five members to solve problems across five distinct tracks.

**[02:04]** So if you haven't already checked out our other problem statements or other webinars, they are actually right now all published on our information document. You can find out more about the problem statements there. So this year, we have an even bigger prize pool, our biggest yet, with first place at $15,000 Singapore dollars, followed by second place $8,000, third place $5,000, fourth and fifth place at $3,000 each. Now people's choice is at $500. So the people's choice winner is actually selected via public voting on Devpost.

**[02:34]** So do rally all your family and friends to show your project a little love and support. So do note that the public voting window will start on 1st September at 3pm and conclude on 7th September at 3pm as well. So here's an overview of our hackathon journey and timeline. Registrations must be done on both our Devpost and also registration form. Now if you haven't already registered, please do so soon and make sure you do so by 1st September at 12pm. Right now, we're also having our full afternoon of five back-to-back technical workshop webinars.

**[03:07]** And here we are, part four of a five-part series. So our next key milestone is the exciting 72-hour challenge and project submission period. Thereafter, our engineers would actually be taking some time to evaluate all your projects and solutions, and we will zoom in on our top 12 teams, which will be invited to TikTok Singapore office for the grand final, which is a full day event. So do know all the dates here are 72 hour challenge and project submission period will kick off tomorrow at 12 o'clock

**[03:35]** and will last to Tuesday at 12 o'clock noon. And then our finals will be on 11 September Friday, it is a full day event 9am to 6pm at our office. So do note that you know registrations must be done on both Devpost and our registration form and also project submissions are on Devpost. All of these are due by 1 September 2026 Tuesday at 12pm. All entries must be on time. Late entries will not be considered. So please be mindful of this strict deadline. So this track, track 4, actually follows our standard judging criteria.

**[04:07]** So for technical execution, there will be 35% of the score. We're looking at a solution that demonstrates strong engineering fundamentals, such as well-structured code, thoughtful architecture, and effective use of APIs or models. your demo should run reliably and technical complexity reflects the deliberate capable decision-making of you and your team. So innovation and problem insight at 20 percent. We're looking for a project that demonstrates originality in both your idea and approach. You should stand out in terms of your sharpness of your problem understanding.

**[04:37]** We want to see how clearly the team has actually framed the challenge, why it matters, and how directly the solution actually addresses it. We're looking also at impact and relevance at 20 percent. The project should have clear potential to deliver value to real users or stakeholders with meaningful reach, tangible benefit and relevance that goes beyond solving for the hackathon prompt alone. As for feasibility and practicality, this is 15% of the score. We're looking at a solution that is realistic and buildable beyond a prototype.

**[05:07]** The approach is technically and operationally sustainable where resource usage is proportionate and the architecture holds under real-world conditions. We're also looking at grounded implementation. Last but not least, presentation and communication, but this is mainly for the final event is 10 percent of the score. We're looking at the team or a solo presenter to be able to communicate the work with clarity. Your pitch should tell a coherent story from problem to solution to potential, and your team or you should be able to respond to questions with depth. What we want to see is that you really have

**[05:38]** a genuine understanding of your own project. So enough from me. Without further ado, I'm very excited to pass the mic to Chenxin for her technical sharing. Okay, hi. Can everybody hear me? Okay, okay, let's get started. Hi, I'm Chenxin.

**[06:06]** This is my background and I graduated from NUS and I major in AI. I joined TikTok in June, yes, in this year. Let's come to our competition part. Okay, everyone, I'm Chenxin, and one of the judges for this track, the challenge is a multi-turn

**[06:36]** conversational e-commerce search, and each team will build an agent that searches, asks you for questions, and remembers preferences. And finally, it will be able to rank the right product. And I will explain the problem, data evaluation, and expected submission for our

**[07:02]** tech gym. Okay, let us start with a basic problem. In normal product search, a user will write one query, and the system returns a list. But real shopping is usually not so simple, because a customer will say, I need shoes without seeing where they will use them and what material they prefer

**[07:34]** or how much they want to spend on the shoes. So these details appears gradually. the customer may also change their mind after seeing the first result. So the agent has four jobs. First one is it must search the catalog. It must ask a useful question when important information is missing. It must remember the customer's active preferences

**[08:04]** and it must re-rank products when new information arrives. The goal is not to create a long conversation, but the goal is to collect better evidence for search. A strong agent asks only when the expected value of the answer is high. So here is an illustrative conversation, like the customer begins with a I need shoes for a trip.

**[08:35]** The message tells us the border category, but it does not tell us enough to rank the products with confidence. A weak system may immediately turn 10 popular shoes for the customer, but a strong agent will firstly identify the missing information that could change the result. It can ask, will work along for a distance? Will have a material or budget preference?

**[09:05]** and the customers then say, yes, I need something water-resistant, comfortable, and under $8, something like that. The agent now has a much better search plan. It can store the use case and comfort requirements, water-resistant, and budget. It can retrieve in a smaller candidate set and re-rank it using all active constraints.

**[09:34]** So I think this example is important for two reasons. First, the conversation is not taken from Amazon data sets. The Amazon reviews contains products and purchase information, but it does not contain a real shopping conversations. The dialogue is generated by our official simulator from a hidden intent card. And second, the agent is not rewarded for talking more.

**[10:05]** Like it is rewarded for finding the target product earlier and the ranking is higher. So this leads to the formal objective for the challenge. How can I turn through next? Oh, this one, sorry. Our formal goal is simple.

**[10:33]** like each session has one hidden target product, and the agent must place the product in its top 10 recommendations, preferably near the top and as in few tiers as possible. The agent may ask questions, recommendation products, or do both in one term. A correct product identifiers creates a hit. a higher rank is better and an earlier first hit

**[11:05]** is better also. So every session has a hard limit of 10 turns and the agent cannot keep asking forever. It must balance information gathering with actions. It also has to replace prior preferences when the customer changes intent. Like each team will build one runnable shopping agent.

**[11:35]** The organizer provides a frozen catalog as we showed in our GitHub, a public development sessions, a user simulator, an evaluator, starter code, and the exact interface contract. And the team will implement the agent in Python. For every term, the agent receives an anonymous customer profile, the latest customer message,

**[12:06]** the turn number, and the required result size. It returns a natural language reply, an optional attribute to ask about, and a ranked list of product identifiers. The official evaluator imports and runs the code locally. Teams do not need to host a website or open a network port.

**[12:37]** So this keeps our competition focused on the agent itself. The scope is intentionally narrow. Teams can use keyword search, embeddings, hybrid retrieval, query rewriting, semantic re-ranking, conversation state, and the clarification

**[13:08]** strategies. It means you can use a lot of algorithms for your agents. And these are the main technical opportunities. You do not need to build a user interface or like train a very large model, process images for the goods, handle real payments or modify the catalog or deploy production infrastructures.

**[13:40]** A beginner team should be able to build a valid entry with BM25 and simple state tracking. A stronger team should win by asking better questions. representing intents more accurately and ranking products more effectively.

**[14:03]** With the task defined, we can now explain where the benchmark data comes from. The benchmark starts from Amazon Reviews 2023, a public research data set published by the McAuley Lab at the University of California, San Diego.

**[14:29]** We use real product metadata and real purchases to or review records. More specifically, we use the official Clothing 5-core leave-last-out split. And earlier eligible purchases from visible history, while the final eligible purchase is traded as a hidden target product.

**[14:58]** Earlier information may contribute only to a safe anonymous aggregate profile. However, the source dataset does not contain real conversations between a shopper and a search agent. Therefore, we create a controlled dialogue layer, a hidden intent card is derived from

**[15:26]** the target product and a scenario policy. The official simulator uses the card to answer the agent's clarification questions in natural language. So, this gives us a useful balance. the catalog and target products come from our real-world records while the conversation

**[15:52]** is well-controlled, reproducible, and safe for evaluation. The customer dialogue is simulated. It is not copied from the Amazon reviews. It is important to say this clearly because the benchmark combines real retrieval evidence with an organizer defined interaction protocol. We use clothing, shoes, and jewellies

**[16:22]** as a competition domain, because clothing is particularly useful conversational category because the products differ by materials, feet, style, color, brand, use cases, size, and price. size and price, a vague request can become much cleaner after one good question. So this creates a natural difficulty ladder.

**[16:51]** Beginners can serve common and well-described products while stronger teams can handle ambiguous requests, changing preferences and more subtle ranking decisions. Here are the exact inputs behind our current benchmark. Our pipelines gained more than 2 million official Clothing 5-core live lost-out records

**[17:19]** against the frozen catalog of 50,000 products. After drawing targets and usable pre-target history to the catalog, about 10K records pass the catalog and the history quality requirements. Those records contain about 1k distinct candidate target products. So from this eligible candidate pool,

**[17:50]** the organizer determined deterministically select about 200 labeled public sessions and 800 organizer-only private sessions. This results in about 1,000 benchmark sessions use distinct users and distinct target products across the public and private splits. This reduces memorization leakage and makes

**[18:17]** the private evaluation a meaningful test of generalization. The purchase signal is real, but the shopping dialogue is generated by us. The Amazon Reviews 2023 does not provide the real multi-turn shopping conversations. After choosing the category and the benchmarks made, we checked which product fields are

**[18:47]** reliable enough for use to expose. The official retrieval space use fields are both useful and available in the frozen catalog. The three core fields are title, features, and details. They normally contain the stronger product evidence.

**[19:15]** We also expose description, categories, score, average_rating counts, and the price when those values are available. Price is very useful, but we treat it as a soft preference. Missing or inconsistent price values should not make a product automatically impossible.

**[19:38]** Rating fields might provide weak popularity or confidence signals, but they do not replace a manual relevance. Teams should decide how to combine the fields rather than assuming that every field has equal quality or coverage. This means it definitely depends on you guys all.

**[20:05]** participants search the same frozen catalog and they are free to build different indexes and weight fields differently. And one team may use BM25, another might combine sparse and dense retrievals, or another can add a semantic re-ranker. The shared schema keeps the comparison fair while leaving room for meaningful technical choices.

**[20:36]** The competition released contains about 50k frozen catalog items and every team received exactly the same catalog. It is small enough to index a normal student laptop, but large enough that simple guessing or manual products rules will not work reliably. and we provide about 200 labeled public sessions for development.

**[21:08]** Teams can run the published evaluator locally, inspect failures, compare versions of their agents, and break down performance by scenario. We keep 800 additional sessions privates for final evaluation. Only the organizer has a private target, hidden intent cards, and simulator states.

**[21:35]** So together, the public and private splits about 1,000 benchmark scenarios. They are separated by user and target product. Each selected session has a distinct target, and there is no users or target overlap between the public and private sets.

**[22:01]** This design gives teams enough public development feedback while preserving a meaningful final test that cannot be optimized directly from the released answers. Our participants receive exactly ten visible catalog fields. They are parent ASIN, title, features, details, description,

**[22:30]** categories, store, average_rating, rating_number, and price. The compressed catalog is is about 19.2 MB, and the complete participant kit is also that size. The repository and released are now public. The release contains catalog catalog.jsonl.gz,

**[23:03]** and so on. Teams can download the catalog or complete kit, edit the starter agent and run the evaluator locally without waiting for the organizer to calculate development scores. And let us now look at how every benchmark session is built.

**[23:36]** Every session follows the same reproducible pipeline. First, we start from the official Clothing 5-core leave-last-out splits. Earlier, eligible purchases from the history while the held out final product becomes the target. Second, we joined the target and the usable pre-target history to the frozen catalog.

**[24:06]** A selected target must exist in the 50K product retrieval space. And there must be enough earlier catalog evidence to build a safe aggregation profile. Third, we determine statistically select distinct users and target products. Participants receive only an anonymous profile

**[24:34]** while the organizer keeps the hidden intent card used by the simulator. Public and private sessions are separately by both users and the target. Finally, we freeze the public set, private set, catalog, schemas, configuration, and check sums. So everything receives the same environment.

**[25:04]** The filtering path start from 2,524,981 official records. After the catalog, drawing, and the history quality filters, 10,187 records remain eligible, containing more than 1,000 distinct candidate targets.

**[25:35]** From that pool, we finally select about 200 public sessions and 800 private sessions. The same pipeline supports the privacy and the leakage controls on the next slide. We protect both evaluation, integrity, and user privacy.

**[26:06]** Automated checks confirms the zero user overlap and the zero target product overlap between the training set and the test set. Target labels in the public development set cannot reappear as a private evaluation answer. The checks also confirm that the hidden target does

**[26:34]** not appear in visible history and that not in-tent car fields are included in our released participant data sets. Teams receive the frozen catalog, a safe anonymous, a great gate profile, simulated customer messages, and public target labels for local development.

**[27:02]** We do not release our raw user identifiers, raw purchase histories, review text, or time steps, because they are very sensitive for you. The organizers along keeps the 8,000 private target labels, hidden intent cards, simulator states, split manifest, and the source data. None of these private artifacts are

**[27:32]** placed in the participant repository or participant kit relays. This prevents teams from recovering an answer through user identifiers, visible history, or hidden fields, while preserving enough contacts for safe personalization. correctness is determined only by exact equality

**[28:00]** with a catalog valid parent ASIN. So next, I will explain the four customer behavior scenarios used by our simulator. OK, the simulator uses four customer behavior scenarios, like 40% are buying sessions.

**[28:28]** In these cases, the customer gives an important hard constraint early, so the retrieval quality matters immediately. Another 40% are browsing sessions. The opening request is vague, and the agent must choose a useful clarification questions instead of guessing.

**[28:58]** And 15% are intent override sessions. One, two, three, three, or four, the customer changes a previous preference. For example, black may become white, or running shoes may become casual sneakers. The agent must replace the old state, not simply add the new words.

**[29:27]** The final 5% are Boundary sessions. The customer may say that they have no preference for requested attributes. A good agent should accept that answer and move on. It should not repeat the same question or invent a constraint. We use the same scenario proportions in our public and private sets.

**[29:57]** The main result uses the overall score, but the evaluator also reports results by scenario. These help teams understand whether they are good at retrieval, clarification, state management or robustness. It also encourages innovation because no single

**[30:23]** naive behavior wins every session. Consider in this short example on turn one a customer says I want black running shoes. The agent stores color equals black and the style equals running. On turn three, the customer says actually make them

**[30:50]** casual white sneakers. A weak agent may append a new message to the old conversation and search for black, white, running and casual at the same time. Those constraints contradict one another so retrieval quality can fail sharply. But a stronger agent recognizes the correction.

**[31:18]** It changes the color from black to white and the style from running to casual. It then rewrites the search query and re-ranks the candidates using only the active intent. This scenario separates simple context accumulation from real conversation state management.

**[31:44]** Teams can implement this with structured slots, recency-aware extraction, or an LLM-based state updater. The method is very open, but the expected behavior is explicit and testable.

**[32:08]** Now let us walk through the evaluator session loop. One evaluation session follows a controlled loop. First, the evaluator calls reset with a session identifier and a anonymous profile. Second, the simulator sends the customer's next message

**[32:36]** according to the scenario policy and hidden intent cards. Third, the agent returns a reply and optional clarification attributes and a ranked recommendation list. The evaluator validates the recommendations. It keeps owning the first term valid unique product

**[33:01]** that exists in the full frozen catalog, it compares them with target using exact parent ASIN matching. If the target appears, evaluated records its rank and first hit return. And the session stops. If there is no hit, the simulator reveals only information allowed by the policy and Next turn begins.

**[33:33]** A miss after turn 10, turn ends to the session. The roles are deliberately separated. The simulator controls customer disclosure, the agent controls questions and the recommendations. The evaluator controls correctness. This gives us every submission in the same test while allowing natural multi-turn interaction,

**[34:04]** the agent contract has two main methods. One is reset starts a new session and provides a anonymous profile. The other is respond receives the latest customer message, current turn number and the requested top K size. The response contains four possible fields. Message is a customer-facing test.

**[34:36]** ask_attribute tells the simulator which preference type the agent wants to clarify. Recommendations is an ordered list of parent ASIN values. usage may contain prompt and completion token cons for cost recording. So this is an Python interface, not a hosted model API

**[35:06]** or fixed network port. Behind it, teams may use an external language model API, a local model or no language models at all, as you like. They only need to follow the inputs and output schema, time limits and dependency rules. Duplicate or invalid identifiers are removed and optional numerical recommendation scores

**[35:37]** are ignored because the list order defines ranking. Exceptions malformed output and times out may count as a misses. Intent override session cannot finish before the change preference has been reviewed, because every submission uses the same interface and validation rules.

**[36:02]** Final technical scoring can be automated consistently. Here comes our technical score. We scored three things. One is accuracy, the other is rank, and the last one is speed. Hit Rate@10 ask us whether the target appears anywhere in agents top 10 list.

**[36:32]** This is the most important metric. Mean Reciprocal Rank, or MRR, rewards a higher position. A target at rank 1 receives 1 point for decision. A target at rank 4 receives 1 quarter.

**[36:57]** Mean Turns To Conversion, or MTTC, measures how clear the first valid hit occurs. A hit on turn 2 records 2. A session with no hit records 11. One step beyond the 10 turn limit. We convert this into a efficiency value between 0 and 1. Here is a worked example.

**[37:25]** Suppose the target appears at rank 4 on turn 2. The hit value says 1. The reciprocal rank is zero points to five. The first hit run is two. These session values are aggregated across the private set. The final technical score is 50% Hit Rate@10

**[37:54]** and 30% MRR and 20% efficiency. Accuracy remains primary, but teams also gain from better ordering and fewer turns. The evaluator uses exact product identifiers, so an LLM never decides whether a recommendation is correct. This makes final judging deterministic fast and inexpensive.

**[38:24]** to fast and inexpensive, we also collect cost information, but we will keep it separate from our core score. For final evaluation, the same definitions are aggregated across a 800 private sessions. rate at 10 is the section of the session that never placed the target and scored 10.

**[38:56]** MRR rewards placing the target near the top of its list. MTTC measures the first successful turn and Nevere Miss is assigned to turn 11. Efficiency converts lower MTTC into a 0 to 1 value. The technical score was hit rate at 50%. MRR at 30% and efficiency at 20%. We also published

**[39:27]** the same metric separately for biome, browsing, intent override and boundary. So a team cannot hide one weak behavior inside the overall average. Okay, final judging follows five criteria you publish in the TechJam problem statement, technical execution accounts for 35 percent, judges consider engineering fundamentals, code

**[39:59]** structure, architecture, effective use of APIs or models, technical complexity and whether the demonstration runs reliably. Innovation and problem insight account for 25 percent. Judges consider the originality of the idea and approach. The clarification of the team's problem understanding and how directly the solution addresses the challenge.

**[40:27]** Impact and relevance account for 25 percent. The project should demonstrate meaningful values for users and stakeholders and potential relevance beyond the hackathon prompt. Feasibility and practicality accounts for 50%. The solution should be realistic,

**[40:52]** buildable beyond the prototype, sustainable, and proportionate in its use of resources. This presentation and communication account for about 10% at the final event. Teams should present a coherent story and demonstrate a strong understanding of their work during questions and others. The challenge if valuation consider coverage through Hit Rate@K ranking precision through

**[41:24]** MRR and top KG rates and the conversational efficiency through MTTC. The solution includes LLM semantic ranking. Teams using external services are responsible for their own credentials, usage limits and costs. So we randomly include the the deterministic weak baseline on all 200

**[41:55]** released public sessions, it uses BM25 retrieval and no large language models, no useful conversation state, and no active clarification strategy. Its purpose is to provide the complete workflow run with only the Python standard library. So the starter achieves about 12.5 percent

**[42:20]** Hit Rate@10 and MRR of 0.06 and then MTTC of 9.81. a reference technical score of about 0.1. These results use the same public sets of frozen catalog starter agent and local evaluator including the participant release.

**[42:46]** intentionally a weak but reproducible starting point. So the low score leaves the substantial Room for Better Candidate Generation, Hybrid Retrieval, state tracking, Clarification Ranking, and Intent Override Handling. We do not publish unverified stronger baseline numbers for the current public set. should run the local evaluators and establish their own measured improvement over the included

**[43:18]** starter. Yes, this is our, I think, this is our suggestion, for your reference. Okay. Well, let's come to the last one. Okay. So to close, the challenge can be summarized

**[43:46]** in three lines. That is, ask better questions, remember customer intents, and rank the product earlier. The data is ready, and the scoring is clear. Students should have a clear path for baseline to innovation. Thank you. Hi, Chenxin, hey Nori. So thank you so much for sharing and I think a lot of people have asked a lot of questions. So what my team has done is

**[44:17]** actually to put all the questions in a separate doc. So Chenxin, you can check your luck. We have actually messaged you to adopt. Right now there's a lot of questions. Maybe you can take some time to take a look at them. And then especially for the very pressing ones that you feel that will benefit the most number of students, you can please feel free to repeat what the question is and then answer accordingly okay yeah thank you okay yeah if we're okay on time and if everyone on the call is okay on time you know we do have a few more

**[44:45]** minutes before the next session so I think we can stay until 4.55 another 10 more minutes maximum for Q&A okay yeah about maybe 8 to 10 minutes thank you everyone yeah so Chenxin when you're ready You know you can pick any question that you feel will be helpful for our students and then you can unmute yourself and also switch back your video on and then you can answer the questions. Thanks everyone. In the meantime you receive some questions that I think my team can

**[45:14]** actually take. I think someone asked about demo video. Basically the demo video is actually up to you whether you want to film yourself presenting or whether or not you want to show how your solution works. It really depends on the track as well but I think our main advice is that what makes you, what would help you most effectively convey your solution, right? So I think as long as you can answer that question, it is up to you how you decide to actually make use of your

**[45:40]** three-minute video, okay? So I think the other thing I wanted to share is that there was another question on prizes, right? So basically the whole hackathon has five prizes plus the people's choice and do note that actually this will be across tracks okay so it's not like one track would have like top one to three four five no okay it's a whole hackathon has one top price and then second, third, fourth, fifth and people's

**[46:06]** tracks across all tracks. Chenxin, would you be able to maybe answer any question quickly so then we can actually make full use of the time that we have left? Let me check for a few questions. Yeah even if you don't look

**[46:35]** at the top. You can look at the chat over here. It's actually the same content. Let me ask first few questions. Like, where will the private evaluator use the same ask_attribute Response Policy as a Reliate Local Evaluator, including repeat other requests and the distinction between the preference and the additional preference? And here is my answer.

**[47:02]** Yes, the final evaluation sessions will use the same deterministic attributes response policy as the released official evaluator, including repeat order requests and distinction between the preference and additional preferences. Teams must use unmodified official evaluators when reporting your final results. Okay, next question is,

**[47:33]** will private user messages follow the released templates or include natural language paraphrases? If the paraphrase are used, can you provide a representative examples or an updated local evaluators? The final evaluation will follow the message templates and the deterministic simulator policy in the released official evaluator.

**[48:03]** No undisclosed natural language paraphrase will be introduced. If any templates are updated, the revised evaluator and representation examples will be published before the submission deadline. Okay, next question is that does each catalog parent

**[48:28]** ASIN represent one concrete color size variant or a parent product with multiple variants? Are private intent cards derived from exactly the same metadata record exposed to participants? Here is the answer, that each parent ASIN represents a parent product, not a specific color or size SKU variant.

**[49:00]** Preview intent cards are derived from the same frozen catalog metadata records exposed to participants. So together with a predefined scenario policy, they do not use hidden variance level attributes or additional product metadata. Okay. Next question that, may teams bundle pre-trained model weights

**[49:31]** or catalog derived embedding index artifacts are their package size limits and must derived indexes be built in memory as startup. My answer is that yes, teams may bundle legally usable pre-trained models with, and the catalog derived embedding or index artifacts like FAISS or something like that,

**[50:01]** provided they are disclosed and reproducible. but there is currently no track-specific package size limits, but large assets should be provided through clearly documented download instruction rather than commit directly to the repository. The right indexes do not need to be rebuilt in memory at startup,

**[50:29]** pre-computed local sidecar artifacts are allowed. Heavy external deployed vector database infrastructure remains out of scope. Next question is that, will the final evaluator use the same metric formula, stopping rules,

**[50:55]** invalid output handling and timeout behavior as a released local evaluator. Yes, final results must be generated using the unmodified official evaluator with the same metric formula, stopping rules, invalid output handling and timeout behavior as released in a local evaluator. Any evaluator updates will be published before the submission deadline and will apply

**[51:27]** equally to the teams. So, oh, sorry, sorry. Oh, okay, okay. Next question is, apart from pre-train models,

**[51:54]** May teams use upstream Amazon Reviews 2023 data or other public corpora for preprocessing or must retrieval features be derived only from our forum catalog? I think teams may use legally accessible upstream Amazon reviews 2023 data

**[52:19]** or other public corpora for preprocessing provided their sources and usage are disclosed. However, external data must not be used to reconstruct our hidden evaluation labels, and all final recommendations must remain valid parent ASIN values from the

**[52:49]** frozen official catalog. Okay, and next question is for LLM usage, are we only allowed to use local LLM and no network access. I think no, because teams can use external LLM

**[53:13]** APIs with network access, local models, or non-LLM approaches, because teams run the final evaluation in our, in their own environments. They must manage their own API credentials using each limits and service availability and costs. And the final one is that it's about our language.

**[53:43]** As I mentioned before, it's only used the Python for your agents. And if you want to use CPU, GPU or something else to help you with building like A&N scoring or embeddings, you can try. I think it's an open combination for all of you guys. Yes. Thank you so much Chenxin and thanks everyone for your Q&A. So I think just wanna share with everybody, right? Due to limited time and also limited resources

**[54:13]** of our engineers time and effort, do note that, you know, we definitely welcome all your Q&A and also we welcome you to write in to APAC Early Careers at tiktok.com for all your questions. But do note that at the end of the day, we can't promise that we will get to everybody and we'll be able to reply everyone. So we seek your kind understanding, but at least as much as we can, we open this channel and we hope to be able to answer some of your questions. And we truly appreciate your time to really analyze our problem statements. And also, like remember, take your chances,

**[54:44]** be bold and be innovative. Feel free to put down your assumptions if it helps, about whatever it is, we really wish you all the best as we actually conquer this hackathon. Now for some final reminders, we're already done with four different webinars and now we're on to our fifth one coming up at five o'clock. So do join us if you're considering to attempt track five, which is about robust detection of AI generated images under real world transformations. So overview of our hackathon journey and timeline again, do note the 72 hour challenge and project submission and also the deadline.

**[55:15]** So this would actually run from 29 August tomorrow at noon all the way to 1st September Tuesday at noon, okay? So registrations must be done on both Devpost and our registration form and project submissions must be done via Devpost all by this deadline and late entries and late project submissions will not be considered, okay? So I'm sure everyone is already very familiar with all these useful resources by Devpost and registration form. I think you've seen that information document. That's where you get the problem statements and also our telegram channel. Do feel free to actually join this channel

**[55:45]** to get all the live real-time updates okay? So thank you so much everyone. Like I mentioned we will try our best to get back to everyone who writes in and also for people who actually took time to join us at Q&A but do note that you know as y'all can see that there are a lot of questions and our engineers can't answer every single one of them. Take chances, be bold, enjoy the process, build with joy and code for change. Thanks everybody and we'll see you at five o'clock if you're joining us for the last webinar.
