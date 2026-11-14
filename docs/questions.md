# AapleSeva — 10 Real Citizen Questions

These are questions a real citizen of Maharashtra might ask an AapleSeva
assistant. The first six map one-to-one onto the project's six canonical
(target) fields:

```
service_name | department | source_url | time_limit_days | designated_officer | first_appellate_officer
```

The published source only carries three of those six (`service_name`,
`department`, `source_url`); the other three are not published. So Q4–Q6 are
questions the real data genuinely cannot answer, with **Q6** being the
mandated example. Q7–Q10 add four more real questions, some answerable by
search and some outside the schema entirely.

> "Your data" below means the real published dataset (`data/records.json`,
> 1058 notified services). The hand-written demo set (`data/sample_records.json`,
> 20 services) fills these fields in, but the official source does not publish
> time limits or officer names — so against the real data those answers are
> `null`.

| # | Citizen question | Card field | Can the data answer? | Answer / why not |
|---|---|---|---|---|
| Q1 | "I want a caste certificate — what is the exact notified service called?" | `service_name` | Yes | `service_name` = "Caste Certificate" (id 3) |
| Q2 | "Which department handles income certificates?" | `department` | Yes | `department` = "Revenue Department" |
| Q3 | "Where is the official portal I apply through?" | `source_url` | Yes | `source_url` = the Aaple Sarkar portal / NS_Service_List PDF URL |
| Q4 | "How many days will my income certificate take to be issued?" | `time_limit_days` | **No** | `time_limit_days` is `null` in the published source; the source carries no time limits |
| Q5 | "Who is the designated officer I submit my application to?" | `designated_officer` | **No** | `designated_officer` is `null`; the source publishes no officer names |
| Q6 | "My application is delayed — who is the first appellate officer I complain to?" | `first_appellate_officer` | **No** | `first_appellate_officer` is `null`; the source publishes no appellate officers |
| Q7 | "I lost my land record — how do I get a certified copy of my 7/12 extract?" | (search) | Yes | matches "Certified Copy of 7/12 Extract" (id 5) by `service_name` |
| Q8 | "Is there a service for a senior citizen certificate, and what category is it?" | (search) | Yes | "Senior Citizen Certificate" (id 7), category "Social Welfare" |
| Q9 | "What documents do I need to submit with my income certificate application?" | — | **No** | the dataset has no documents-required field |
| Q10 | "How do I track the status of my application online after submitting?" | — | **No** | the dataset has no application-status / tracking field |

Q1–Q6 walk the six target fields in order, ending at Q6 on the first appellate
officer — a genuinely common citizen concern that the published AapleSeva data
simply does not contain. Q7–Q10 mark the boundary of the dataset: search can
find services by name (Q7, Q8), but anything about required documents (Q9),
fees, or live status (Q10) is outside the schema entirely.

These map cleanly onto the API: Q1, Q2, Q3, Q7, Q8 are answerable through
`GET /records/{id}` or `GET /search?q=`; Q4, Q5, Q6, Q9, Q10 are not, and an
honest assistant should say so rather than invent an officer or a time limit.
