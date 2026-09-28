-- Run against the current filtered transaction table built on the SQL page.
-- A query result identifies patterns for review, not criminal conduct.

SELECT method, COUNT(*) AS transactions, ROUND(AVG(amount), 2) AS mean_amount
FROM transactions GROUP BY method ORDER BY transactions DESC;

SELECT sender_key, DATE(time) AS day, COUNT(*) AS outgoing_count
FROM transactions GROUP BY sender_key, DATE(time)
HAVING COUNT(*) >= 5 ORDER BY outgoing_count DESC;

SELECT receiver_key, DATE(time) AS day,
       COUNT(DISTINCT sender_key) AS distinct_senders, ROUND(SUM(amount), 2) AS inbound
FROM transactions GROUP BY receiver_key, DATE(time)
HAVING COUNT(DISTINCT sender_key) >= 3 ORDER BY distinct_senders DESC;

SELECT a.receiver_key AS account, COUNT(*) AS inbound_outbound_pairs
FROM transactions a JOIN transactions b ON a.receiver_key = b.sender_key
 AND julianday(b.time) > julianday(a.time)
 AND julianday(b.time) - julianday(a.time) <= 1
GROUP BY a.receiver_key ORDER BY inbound_outbound_pairs DESC LIMIT 25;

SELECT from_bank, to_bank, COUNT(*) AS transactions, ROUND(SUM(amount), 2) AS volume
FROM transactions GROUP BY from_bank, to_bank ORDER BY volume DESC LIMIT 20;

SELECT score, COUNT(*) AS transactions, SUM(alert) AS review_queue
FROM transactions GROUP BY score ORDER BY score DESC;

SELECT DATE(time) AS day, COUNT(*) AS transactions,
       SUM(CASE WHEN label = 1 THEN 1 ELSE 0 END) AS simulated_positives
FROM transactions GROUP BY DATE(time) ORDER BY day;

SELECT sender_key, COUNT(DISTINCT receiver_key) AS counterparties
FROM transactions GROUP BY sender_key ORDER BY counterparties DESC LIMIT 25;
