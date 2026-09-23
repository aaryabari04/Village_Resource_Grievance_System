-- ===================================================
-- Village Resources and Grievance Management System
-- Initial Seed Data: Departments, Resources, Announcements
-- ===================================================

-- Departments
INSERT OR IGNORE INTO departments (id, name, contact, description) VALUES
(1, 'Water Department', '+91 98220 55001', 'Manages village drinking water supply, borewells, overhead tanks, and pipeline maintenance.'),
(2, 'Electricity Department', '+91 98220 55002', 'Oversees power grid, streetlights, agricultural pump feeders, and transformer repairs.'),
(3, 'Public Works Department', '+91 98220 55003', 'Maintains village roads, bridges, drainage channels, and public building infrastructure.'),
(4, 'Health Department', '+91 98220 55004', 'Coordinates Primary Health Centre, immunization, maternal health, and emergency medical services.'),
(5, 'Education Department', '+91 98220 55005', 'Oversees primary & secondary schools, midday meals, scholarships, and adult literacy drives.'),
(6, 'Sanitation Department', '+91 98220 55006', 'Responsible for daily waste collection, village cleanliness, public toilets, and fogging operations.');

-- Resources
INSERT OR IGNORE INTO resources (id, name, category, location, contact, availability, description, created_at) VALUES
(1, 'Primary Health Centre (PHC)', 'Health', 'Near Main Gram Panchayat, Main Road', '+91 98220 11001', '24x7 Emergency, OPD 9 AM - 4 PM', 'Comprehensive medical care with 6-bed facility, maternity ward, emergency ambulance, and free generic medicine dispensary.', '2026-01-10 09:00:00'),
(2, 'Government Primary & Secondary School', 'Education', 'School Para, Ward No. 2', '+91 98220 11002', 'Monday to Saturday: 8:00 AM - 2:30 PM', 'State-board affiliated school offering classes from 1st to 10th standard with smart classroom and computer lab.', '2026-01-10 09:30:00'),
(3, 'Gram Panchayat Administrative Office', 'Administration', 'Panchayat Bhavan, Central Square', '+91 98220 11003', 'Monday to Friday: 10:00 AM - 5:00 PM', 'Nodal office for birth/death certificates, caste/residence verification, property tax, and welfare scheme enrollments.', '2026-01-10 10:00:00'),
(4, 'Central Water Supply & Filtration Station', 'Utilities', 'North Reservoir Hill', '+91 98220 11004', 'Daily 6:00 AM - 10:00 AM & 5:00 PM - 8:00 PM', 'Purified potable water distribution pumping station feeding household tap connections and public standposts.', '2026-01-10 10:30:00'),
(5, 'Sarvajanik Community Hall', 'Public Facility', 'East Gate, Near Hanuman Temple', '+91 98220 11005', 'Open for booking 8:00 AM - 10:00 PM', 'Spacious hall with capacity for 500 people, available for village meetings, social celebrations, and disaster relief shelters.', '2026-01-10 11:00:00'),
(6, 'Village Main Bus Stop & Transit Point', 'Transport', 'Highway Crossing, South Entry', '+91 98220 11006', '24 Hours Open (Bus schedule 5 AM - 10 PM)', 'Connecting state transport buses to district headquarters, tehsil center, and railway junction.', '2026-01-10 11:30:00'),
(7, 'Village Public Knowledge Library', 'Education', '1st Floor, Panchayat Bhavan', '+91 98220 11007', 'Tuesday to Sunday: 9:00 AM - 6:00 PM', 'Contains over 3,000 books, competitive exam guides, daily newspapers in English, Marathi, and Hindi, plus free Wi-Fi.', '2026-01-10 12:00:00'),
(8, 'Anganwadi Welfare Centre No. 1', 'Health', 'West Para, Near Shanti Nagar', '+91 98220 11008', 'Monday to Saturday: 8:30 AM - 1:30 PM', 'Early childhood care, nutritional supplements for pregnant mothers, and monthly immunization programs.', '2026-01-10 12:30:00');

-- Announcements
INSERT OR IGNORE INTO announcements (id, title, description, announcement_date, created_at) VALUES
(1, 'Free Mega Health & Eye Checkup Camp', 'A free medical diagnosis and eye examination camp will be held at Primary Health Centre on Saturday. Free eyeglasses and medicines will be distributed to eligible senior citizens and children.', '2026-03-28', '2026-03-20 10:00:00'),
(2, 'Annual Gram Sabha General Assembly', 'All village residents are cordially invited to attend the Gram Sabha meeting at Community Hall to discuss the village development budget, road construction priorities, and drinking water expansion.', '2026-04-05', '2026-03-21 11:30:00'),
(3, 'Scheduled Drinking Water Pipeline Maintenance', 'Routine cleaning and chlorination of the overhead storage tank will take place this Thursday. Water supply will be interrupted between 11:00 AM and 4:00 PM. Please store sufficient water in advance.', '2026-03-26', '2026-03-22 09:15:00'),
(4, 'PM-Kisan & Solar Agricultural Pump Subsidy Scheme', 'Registration desk for the PM-Kisan installment verification and state 90% subsidy for solar agricultural pumps is open at Gram Panchayat office till the 15th of next month. Bring 7/12 extract and Aadhaar card.', '2026-04-15', '2026-03-22 14:00:00');
