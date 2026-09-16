-- ===========================================================================
-- Sample data. Run once, after schema.sql, to get a working system to click
-- through. Safe to re-run: every statement clears its own rows first.
-- ===========================================================================

-- -- 1. People --------------------------------------------------------------
DELETE FROM `mis-gempundit.Content_FMS.Users` WHERE user_id IN (1001,1002,1003,1004);
INSERT INTO `mis-gempundit.Content_FMS.Users`
  (user_id, username, email, password_hash, role, is_active, created_at, updated_at)
VALUES
  (1001,'Vivek',  'vivek@gempundit.com',  '', 'approver', TRUE, DATETIME '2026-08-01 10:00:00', DATETIME '2026-08-01 10:00:00'),
  (1002,'Kirti',  'kirti@gempundit.com',  '', 'writer',   TRUE, DATETIME '2026-08-01 10:00:00', DATETIME '2026-08-01 10:00:00'),
  (1003,'Sourabh','sourabh@gempundit.com','', 'admin',    TRUE, DATETIME '2026-08-01 10:00:00', DATETIME '2026-08-01 10:00:00'),
  (1004,'Neelav', 'neelav@gempundit.com', '', 'viewer',   TRUE, DATETIME '2026-08-01 10:00:00', DATETIME '2026-08-01 10:00:00');

-- -- 2. What the AI produced -------------------------------------------------
DELETE FROM `mis-gempundit.Content_FMS.AI_Content_Queue` WHERE unique_key LIKE 'CNT-2026-%';
INSERT INTO `mis-gempundit.Content_FMS.AI_Content_Queue`
  (unique_key, generated_at, status, category, gemstone_name, search_term, secondary_keywords,
   search_volume, keyword_difficulty, intent, content_type, language, priority, planned_date,
   target_url, meta_title, meta_description, ai_draft, ai_draft_url, word_count,
   ai_model, ai_confidence, research_notes)
VALUES
 ('CNT-2026-0001', DATETIME '2026-09-14 06:12:00','READY','Gemstones','Blue Sapphire',
  'blue sapphire price per carat','neelam stone price, blue sapphire rate india, ceylon sapphire cost',
  18100, 54,'Commercial','Blog','en','High', DATE '2026-09-22',
  'https://www.gempundit.com/blue-sapphire-neelam',
  'Blue Sapphire Price Per Carat in India (2026 Guide)',
  'What a certified blue sapphire actually costs per carat in India, and the four things that move the price.',
  "Blue sapphire is priced per carat, and the spread is wider than most buyers expect: a commercial-grade stone can sit near Rs 1,500 per carat while an unheated Kashmir sapphire of the same weight runs into lakhs.\n\nFour things decide where a stone lands. Origin comes first. Kashmir commands the highest premium, followed by Burma and then Ceylon, which is where most of the market actually buys. Colour is second: the trade pays for a saturated cornflower blue that holds its tone under both daylight and incandescent light.\n\nClarity is third, and sapphires are judged more leniently than diamonds here. Fine silk is expected and can even lift the price when it produces a velvety appearance. Treatment is the last and most abused variable. Heat treatment is common and disclosed honestly by reputable sellers; it lowers value against an unheated stone of equal quality but does not make a stone fake.\n\nAlways buy against a lab certificate that states origin and treatment.",
  NULL, 198,'gemini-2.5-pro', 0.91,
  'SERP is dominated by marketplace listings; only two pages give an actual price table. Gap: nobody breaks price down by origin.'),

 ('CNT-2026-0002', DATETIME '2026-09-14 06:18:00','READY','Astrology','Yellow Sapphire',
  'who should wear yellow sapphire','pukhraj kis rashi ko pehnna chahiye, yellow sapphire for which zodiac',
  12400, 41,'Informational','Blog','en','High', DATE '2026-09-20',
  NULL,
  'Who Should Wear Yellow Sapphire? Zodiac, Rules and Timing',
  'Which rashis benefit from pukhraj, who should avoid it, and the day and finger that tradition prescribes.',
  "Yellow sapphire, or pukhraj, is the gemstone of Jupiter, and Vedic astrology treats it as the most broadly beneficial of the nine primary stones.\n\nSagittarius and Pisces are ruled by Jupiter, so natives of both signs can wear pukhraj without a supporting condition. Aries, Cancer, Leo and Scorpio are considered friendly to Jupiter and are usually cleared to wear it as well.\n\nTaurus, Virgo, Libra, Capricorn and Aquarius are the cautious group. For these signs Jupiter is either neutral or a functional malefic depending on house placement, and a chart reading should come before the stone.\n\nTradition sets the practicalities: gold, the index finger of the right hand, worn on a Thursday morning during the waxing moon, in a minimum of five carats.",
  'https://docs.google.com/document/d/1pukhraj-draft-sample/edit', 176,'gemini-2.5-pro', 0.88,
  'High-volume evergreen. Competing pages are thin and repeat each other verbatim.'),

 ('CNT-2026-0003', DATETIME '2026-09-13 07:40:00','READY','Rudraksha','5 Mukhi Rudraksha',
  '5 mukhi rudraksha benefits','panch mukhi rudraksha ke fayde, 5 face rudraksha uses',
  9900, 33,'Informational','Product tab','en','Medium', DATE '2026-09-19',
  'https://www.gempundit.com/rudraksha/5-mukhi',
  '5 Mukhi Rudraksha: Benefits, Who Can Wear It and How',
  'The most widely worn rudraksha, what it is believed to do, and the rules for wearing it daily.',
  "The five-faced rudraksha is the most common bead on the mala and the one almost anyone can wear. It is associated with Kalagni Rudra, a form of Shiva, and with Jupiter among the planets.\n\nPractitioners wear it for mental steadiness. The traditional claims centre on calmer thinking, better focus during study or meditation, and relief from restlessness. Unlike most other mukhis, it carries no restriction by zodiac sign, age or gender.\n\nA genuine bead has five clean vertical clefts running end to end, sinks in water when untreated, and comes with an X-ray report from a recognised lab. Nepal beads are larger and more expensive; Indonesian beads are smaller and better suited to a 108-bead mala.",
  NULL, 152,'gemini-2.5-pro', 0.93,
  'Product tab rewrite. Existing copy on the page is four years old and has no wearing instructions.'),

 ('CNT-2026-0004', DATETIME '2026-09-12 09:05:00','READY','Gemstones','Emerald',
  'emerald vs green tourmaline','panna vs green tourmaline, which green stone to buy',
  2900, 28,'Commercial','Blog','en','Medium', DATE '2026-09-24',
  NULL,
  'Emerald vs Green Tourmaline: Which Green Stone to Buy',
  'How panna and green tourmaline differ on hardness, price, treatment and astrological use.',
  "Both stones are green and both are sold as substitutes for each other, which is where buyers get into trouble.\n\nEmerald is beryl, sits at 7.5 to 8 on the Mohs scale, and is almost always fracture-filled with oil or resin. Green tourmaline is harder to damage in daily wear despite a similar hardness, because it lacks emerald's characteristic internal fracturing.\n\nOn price, a certified Colombian emerald of good colour costs several times a comparable tourmaline. For a buyer who wants green for appearance alone, tourmaline is the better value.\n\nAstrologically they are not interchangeable. Panna is the stone of Mercury; green tourmaline has no equivalent standing in Vedic practice and should not be substituted where a chart prescribes emerald.",
  NULL, 165,'gemini-2.5-pro', 0.85,
  'Low competition, decent commercial intent. Nobody covers the astrological non-equivalence.'),

 ('CNT-2026-0005', DATETIME '2026-09-12 09:20:00','READY','Gemstones','Ruby',
  'how to identify real ruby','asli manik ki pehchan, real vs fake ruby test',
  14800, 47,'Informational','Blog','en','High', DATE '2026-09-21',
  'https://www.gempundit.com/ruby-manik',
  'How to Identify a Real Ruby: Tests That Actually Work',
  'The at-home checks worth doing, the ones that prove nothing, and what only a lab can tell you.',
  "Most of the ruby-testing advice online is folklore. The scratch test damages your stone and tells you almost nothing. The breath test is meaningless. Rubbing a ruby on a cloth to see if it leaves a streak will identify a dyed quartz and nothing else.\n\nWhat does work at home is limited but real. Hold the stone under a strong light and look for natural inclusions: silk, colour zoning, tiny crystals. A flawless red stone at a low price is glass or synthetic, without exception. Check for gas bubbles with a 10x loupe; natural rubies do not contain them.\n\nEverything else needs equipment. Refractive index, fluorescence under UV and spectroscopy separate natural from synthetic, and only a lab report from GRS, GIA or IGI settles the question of treatment.",
  NULL, 158,'gemini-2.5-pro', 0.90,
  'Highest-volume term in the set. Current ranking pages repeat the scratch-test myth.'),

 ('CNT-2026-0006', DATETIME '2026-09-10 11:30:00','READY','Astrology','Gomed',
  'gomed stone benefits and side effects','hessonite garnet benefits, gomed nuksan',
  8100, 36,'Informational','Blog','en','Medium', DATE '2026-09-18',
  NULL,
  'Gomed Stone: Benefits and the Side Effects Nobody Mentions',
  'What hessonite is prescribed for, and the warning signs that mean you should take it off.',
  "Gomed is hessonite garnet and the gemstone of Rahu, which makes it the most volatile stone in the Vedic set.\n\nIt is prescribed during Rahu mahadasha, for confusion that has no obvious cause, and for stalled legal matters. Practitioners report its effect as faster and blunter than other stones.\n\nThe side effects deserve more attention than they normally get. A wrongly prescribed gomed is associated with disturbed sleep, agitation and a run of small misfortunes in the first fortnight. Traditional guidance is to remove it immediately if that pattern shows and not to reintroduce it without a fresh reading.\n\nIt should never be worn alongside pearl, yellow sapphire or red coral.",
  NULL, 149,'gemini-2.5-pro', 0.87,
  'Side-effects angle is the gap; every competing page only lists benefits.'),

 ('CNT-2026-0007', DATETIME '2026-09-09 14:00:00','READY','Gemstones','Pearl',
  'best gemstone for money','which stone attracts wealth, dhan ke liye ratna',
  33100, 68,'Informational','Blog','en','Low', DATE '2026-10-02',
  NULL,
  'Best Gemstone for Money and Wealth',
  'The stones traditionally associated with prosperity.',
  "Wearing the right gemstone can transform your finances overnight. Emerald guarantees business success, yellow sapphire brings instant wealth, and diamond ensures a life free of money problems.\n\nThousands of people have become rich after wearing these stones. Simply choose any one of them and results will follow within days, regardless of your birth chart.",
  NULL, 62,'gemini-2.5-pro', 0.34,
  'Very high volume but the draft came back making guaranteed-outcome claims. Flagged low confidence.'),

 ('CNT-2026-0008', DATETIME '2026-09-15 05:50:00','READY','Gemstones','Red Coral',
  'red coral for mangal dosha','moonga for manglik, red coral mangal dosh remedy',
  6600, 39,'Informational','Blog','en','High', DATE '2026-09-25',
  NULL,
  'Red Coral for Mangal Dosha: What It Does and When to Wear It',
  'How moonga is used against manglik dosha, with the placements where it is the wrong remedy.',
  "Red coral is the stone of Mars, which makes it the default suggestion whenever mangal dosha comes up. That default is wrong about as often as it is right.\n\nMoonga strengthens Mars. Where the dosha comes from a weak or afflicted Mars, strengthening it helps. Where Mars is already strong and badly placed, adding to it makes the situation worse, and the correct remedy is pacification rather than reinforcement.\n\nThe practical rule is that the first, fourth, seventh, eighth and twelfth house placements all need to be read separately before anyone hands you a coral.",
  NULL, 128,'gemini-2.5-pro', 0.89,
  'Seasonal lift around wedding season. Nuance on when NOT to wear it is missing everywhere.'),

 ('CNT-2026-0009', DATETIME '2026-09-15 06:02:00','READY','Yantra','Shree Yantra',
  'shree yantra placement direction','shri yantra kis disha mein rakhen, sri yantra vastu',
  5400, 31,'Informational','FAQ','en','Medium', DATE '2026-09-28',
  'https://www.gempundit.com/yantra/shree-yantra',
  'Shree Yantra Placement: Direction, Room and Common Mistakes',
  'Where to keep a Shree Yantra at home or in a shop, and the placements to avoid.',
  "A Shree Yantra works on placement more than on material. North-east is the prescribed direction for a home, with the yantra raised off the floor and facing so the viewer looks at it from the west.\n\nIn a shop or office the cash counter placement is the common one, again facing east or north. It should not sit in a bedroom, a bathroom wall, or below any other object.\n\nThe mistakes that come up most often are keeping it on the floor, keeping it unclean, and keeping more than one in a single room.",
  NULL, 118,'gemini-2.5-pro', 0.86,
  'Straightforward FAQ. Good internal linking target for the yantra category.'),

 ('CNT-2026-0010', DATETIME '2026-09-15 06:15:00','READY','Gemstones','Opal',
  'opal stone benefits for which rashi','opal kis rashi ke liye, white opal astrology',
  4400, 29,'Informational','Blog','en','Low', DATE '2026-10-06',
  NULL,
  'Opal Stone: Which Rashi It Suits and What It Is Used For',
  'Opal as the Venus stone, the signs it fits, and how it compares with diamond.',
  "Opal stands in for diamond as the gemstone of Venus, which makes it the affordable route to a Shukra remedy.\n\nTaurus and Libra are ruled by Venus and can wear opal without further qualification. Capricorn, Aquarius, Gemini and Virgo are generally cleared. Aries, Cancer, Leo and Scorpio should get a chart read first.\n\nIt is worn in silver or white gold on the ring finger, on a Friday, in a minimum of three carats. Opal is soft and porous, so it needs to come off before swimming, cleaning or anything involving chemicals.",
  NULL, 122,'gemini-2.5-pro', 0.84,
  'Lower priority. Useful as a supporting page for the Venus cluster.'),

 ('CNT-2026-0011', DATETIME '2026-09-15 06:31:00','HOLD','Gemstones','Cats Eye',
  'cats eye stone price','lehsunia stone rate, chrysoberyl cat eye price india',
  7200, 44,'Commercial','Blog','en','Medium', DATE '2026-10-08',
  NULL,'Cat''s Eye Stone Price in India','Current lehsunia rates and what drives them.',
  "Draft held back pending a price check against the current catalogue.",
  NULL, 12,'gemini-2.5-pro', 0.51,
  'On hold: pricing data in the draft did not match the live catalogue.'),

 ('CNT-2026-0012', DATETIME '2026-09-15 06:44:00','READY','Astrology','Panna',
  'emerald for mercury remedy','panna for budh grah, emerald mercury astrology',
  3600, 26,'Informational','Blog','en','Medium', DATE '2026-10-04',
  NULL,
  'Emerald as a Mercury Remedy: Who It Helps',
  'When panna is prescribed for Budh, the signs it suits, and how it is worn.',
  "Panna is the gemstone of Mercury and is prescribed where Budh is weak: hesitant speech, difficulty with numbers, business decisions that keep going wrong.\n\nGemini and Virgo are ruled by Mercury and can wear it directly. Taurus, Libra, Capricorn and Aquarius are friendly placements. The remaining signs need a reading.\n\nIt is set in gold or silver, worn on the little finger of the working hand, on a Wednesday morning, at a minimum of three carats.",
  NULL, 108,'gemini-2.5-pro', 0.88,
  'Pairs with CNT-2026-0004. Link the two once both are live.');

-- -- 3. Items already pulled into the workflow --------------------------------
DELETE FROM `mis-gempundit.Content_FMS.Content_Approval_Workflow` WHERE unique_key LIKE 'CNT-2026-%';

-- The draft arrives: one DRAFT_RECEIVED per item, carrying the seed row verbatim.
INSERT INTO `mis-gempundit.Content_FMS.Content_Approval_Workflow`
  (event_id, timestamp, unique_key, category, action, content_text, content_url,
   word_count, search_keywords, search_volume, revision_number, source_row_id, source_payload)
SELECT
  CONCAT('evt-', REPLACE(q.unique_key, 'CNT-2026-', ''), '-01'),
  DATETIME_ADD(q.generated_at, INTERVAL 7 MINUTE),
  q.unique_key, q.category, 'DRAFT_RECEIVED',
  q.ai_draft, q.ai_draft_url, q.word_count, q.search_term, q.search_volume,
  0, q.unique_key, TO_JSON_STRING(q)
FROM `mis-gempundit.Content_FMS.AI_Content_Queue` q
WHERE q.unique_key IN ('CNT-2026-0001','CNT-2026-0002','CNT-2026-0003',
                       'CNT-2026-0004','CNT-2026-0005','CNT-2026-0006','CNT-2026-0007');

-- Everything that happened after. 0001 and 0002 stay untouched on Vivek's desk.
INSERT INTO `mis-gempundit.Content_FMS.Content_Approval_Workflow`
  (event_id, timestamp, unique_key, category, action, actor_user_id, actor_email,
   assignee_user_id, assignee_email, content_text, content_url, word_count,
   comment, revision_number)
VALUES
 -- 0003: approved and sitting with Kirti
 ('evt-0003-02', DATETIME '2026-09-13 10:15:00','CNT-2026-0003','Rudraksha','APPROVED',
  1001,'vivek@gempundit.com', NULL,NULL, NULL,NULL,NULL,
  'Good base. Add the wearing ritual and the lab-report line before it goes on the tab.', NULL),
 ('evt-0003-03', DATETIME '2026-09-13 10:15:00','CNT-2026-0003','Rudraksha','ALLOCATED',
  1001,'vivek@gempundit.com', 1002,'kirti@gempundit.com', NULL,NULL,NULL, NULL, NULL),

 -- 0004: Kirti submitted, waiting on review
 ('evt-0004-02', DATETIME '2026-09-12 12:40:00','CNT-2026-0004','Gemstones','APPROVED',
  1001,'vivek@gempundit.com', NULL,NULL,NULL,NULL,NULL,
  'Keep the astrology paragraph, it is the whole differentiator.', NULL),
 ('evt-0004-03', DATETIME '2026-09-12 12:40:00','CNT-2026-0004','Gemstones','ALLOCATED',
  1001,'vivek@gempundit.com', 1002,'kirti@gempundit.com', NULL,NULL,NULL,NULL,NULL),
 ('evt-0004-04', DATETIME '2026-09-15 16:20:00','CNT-2026-0004','Gemstones','SUBMITTED',
  1002,'kirti@gempundit.com', 1002,'kirti@gempundit.com',
  "Both stones are green, both are sold as substitutes for the other, and that is exactly where buyers lose money.\n\nEmerald is beryl. It sits at 7.5 to 8 on the Mohs scale and is almost always fracture-filled with oil or resin, which is disclosed by any seller worth buying from. Green tourmaline reaches a similar hardness but survives daily wear better, because it lacks the internal fracturing that defines emerald.\n\nOn price the gap is wide. A certified Colombian emerald of good colour costs several times a comparable tourmaline of the same carat weight. If you want a green stone purely for how it looks, tourmaline is the honest recommendation and we will tell you so.\n\nAstrologically they are not interchangeable, and this is the part most comparison pages leave out. Panna is the stone of Mercury and carries a specific role in Vedic practice. Green tourmaline has no equivalent standing. Where a chart prescribes emerald, a tourmaline does not substitute for it at any price.\n\nBuy emerald against a lab certificate that states origin and the extent of filling. Buy tourmaline on colour and clarity alone.",
  NULL, 189, 'Expanded the astrology section as asked and added a buying line at the end.', 1),

 -- 0005: bounced back, now with Kirti again
 ('evt-0005-02', DATETIME '2026-09-12 13:05:00','CNT-2026-0005','Gemstones','APPROVED',
  1001,'vivek@gempundit.com', NULL,NULL,NULL,NULL,NULL, NULL, NULL),
 ('evt-0005-03', DATETIME '2026-09-12 13:05:00','CNT-2026-0005','Gemstones','ALLOCATED',
  1001,'vivek@gempundit.com', 1002,'kirti@gempundit.com', NULL,NULL,NULL,NULL,NULL),
 ('evt-0005-04', DATETIME '2026-09-14 11:10:00','CNT-2026-0005','Gemstones','SUBMITTED',
  1002,'kirti@gempundit.com', 1002,'kirti@gempundit.com',
  "Most ruby-testing advice online is folklore. The scratch test damages the stone and proves nothing. The breath test is meaningless.\n\nWhat works at home is limited. Look for natural inclusions under strong light: silk, colour zoning, small crystals. A flawless red stone at a low price is glass or synthetic. Check for gas bubbles with a 10x loupe.\n\nEverything else needs a lab.",
  NULL, 68, 'First pass.', 1),
 ('evt-0005-05', DATETIME '2026-09-15 09:30:00','CNT-2026-0005','Gemstones','REWRITE_REQUESTED',
  1001,'vivek@gempundit.com', 1002,'kirti@gempundit.com', NULL,NULL,NULL,
  'Too short for the search volume this term carries. Name the labs, explain what refractive index and UV fluorescence actually separate, and keep the debunking section — that is why we will outrank the existing pages.', NULL),

 -- 0006: signed off
 ('evt-0006-02', DATETIME '2026-09-10 15:00:00','CNT-2026-0006','Astrology','APPROVED',
  1001,'vivek@gempundit.com', NULL,NULL,NULL,NULL,NULL,
  'The side-effects angle is the reason to run this. Make it the lead.', NULL),
 ('evt-0006-03', DATETIME '2026-09-10 15:00:00','CNT-2026-0006','Astrology','ALLOCATED',
  1001,'vivek@gempundit.com', 1002,'kirti@gempundit.com', NULL,NULL,NULL,NULL,NULL),
 ('evt-0006-04', DATETIME '2026-09-11 17:45:00','CNT-2026-0006','Astrology','SUBMITTED',
  1002,'kirti@gempundit.com', 1002,'kirti@gempundit.com',
  "Gomed is hessonite garnet and the gemstone of Rahu, which makes it the most unpredictable stone in the Vedic set. Most pages about it list only benefits. That is the part worth correcting first.\n\nA wrongly prescribed gomed shows up quickly. Disturbed sleep, unexplained agitation and a run of small reversals inside the first fortnight are the pattern practitioners watch for. The traditional instruction is to remove the stone at once and not to put it back on without a fresh reading. Nobody should be talked past that.\n\nWhere it is correctly indicated, gomed is prescribed during Rahu mahadasha, for confusion with no obvious source, and for legal matters that have stalled. Its effect is described as faster and blunter than the other stones, which is consistent with how quickly a wrong prescription announces itself.\n\nIt is never worn alongside pearl, yellow sapphire or red coral. Those combinations are the most common mistake we see in customer queries.",
  'https://docs.google.com/document/d/1gomed-final-sample/edit', 176,
  'Led with the side effects as discussed. Doc link has the formatted version with headings.', 1),
 ('evt-0006-05', DATETIME '2026-09-12 10:05:00','CNT-2026-0006','Astrology','COMPLETED',
  1001,'vivek@gempundit.com', NULL,NULL,NULL,NULL,NULL,
  'Exactly right. Send it to publishing.', NULL),

 -- 0007: killed at stage 2
 ('evt-0007-02', DATETIME '2026-09-09 16:30:00','CNT-2026-0007','Gemstones','REJECTED',
  1001,'vivek@gempundit.com', NULL,NULL,NULL,NULL,NULL,
  'Guaranteed-outcome claims. We cannot publish this and it should not have been drafted. Re-run the brief with the compliance rules attached.', NULL);
