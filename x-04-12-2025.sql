-- phpMyAdmin SQL Dump
-- version 5.2.2
-- https://www.phpmyadmin.net/
--
-- Host: mariadb
-- Generation Time: Dec 04, 2025 at 01:18 PM
-- Server version: 10.6.20-MariaDB-ubu2004
-- PHP Version: 8.2.27

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `x`
--

DELIMITER $$
--
-- Procedures
--
CREATE DEFINER=`root`@`%` PROCEDURE `get_all_users` ()   SELECT * FROM users$$

CREATE DEFINER=`root`@`%` PROCEDURE `get_posts` (IN `my_offset` INT UNSIGNED)   SELECT * FROM users JOIN posts ON user_pk = post_user_fk  ORDER BY post_created_at DESC LIMIT 11 OFFSET my_offset$$

CREATE DEFINER=`root`@`%` PROCEDURE `get_users` (IN `my_offset` INT UNSIGNED)   SELECT * FROM users ORDER BY user_username ASC LIMIT 11 OFFSET my_offset$$

DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `comments`
--

CREATE TABLE `comments` (
  `comment_pk` char(32) NOT NULL,
  `comment_user_fk` char(32) NOT NULL,
  `comment_message` varchar(280) NOT NULL,
  `post_fk` char(32) NOT NULL,
  `comment_created_at` bigint(20) UNSIGNED NOT NULL DEFAULT 0,
  `comment_updated_at` bigint(20) UNSIGNED NOT NULL DEFAULT 0,
  `comment_deleted_at` bigint(20) UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `comments`
--

INSERT INTO `comments` (`comment_pk`, `comment_user_fk`, `comment_message`, `post_fk`, `comment_created_at`, `comment_updated_at`, `comment_deleted_at`) VALUES
('d70ecad97bfb4bf5aba351cbfc68f5ae', '6b48c6095913402eb4841529830e5415', 'testing count', '6a67456ad548482e9a5fd809ecc9b102', 1764250456, 0, 1764514394);

-- --------------------------------------------------------

--
-- Table structure for table `follows`
--

CREATE TABLE `follows` (
  `followed_fk` char(32) NOT NULL,
  `follower_fk` char(32) NOT NULL,
  `follow_created_at` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `follows`
--

INSERT INTO `follows` (`followed_fk`, `follower_fk`, `follow_created_at`) VALUES
('38821e8c53b146b591933bed979e2016', '6b48c6095913402eb4841529830e5415', 1764852255);

--
-- Triggers `follows`
--
DELIMITER $$
CREATE TRIGGER `decrease_follow_amount` AFTER DELETE ON `follows` FOR EACH ROW UPDATE users
SET user_total_followers = user_total_followers - 1
WHERE user_pk = OLD.followed_fk
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `increase_follow_amount` AFTER INSERT ON `follows` FOR EACH ROW UPDATE users
SET user_total_followers = user_total_followers + 1
WHERE user_pk = NEW.followed_fk
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `likes`
--

CREATE TABLE `likes` (
  `liked_post_fk` char(32) NOT NULL,
  `liker_user_fk` char(32) NOT NULL,
  `like_created_at` bigint(20) UNSIGNED NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Triggers `likes`
--
DELIMITER $$
CREATE TRIGGER `decreate_like_amount` AFTER DELETE ON `likes` FOR EACH ROW UPDATE posts
SET post_total_likes = post_total_likes - 1
WHERE post_pk = OLD.liked_post_fk
$$
DELIMITER ;
DELIMITER $$
CREATE TRIGGER `increase_like_amount` AFTER INSERT ON `likes` FOR EACH ROW UPDATE posts
SET post_total_likes = post_total_likes + 1
WHERE post_pk = NEW.liked_post_fk
$$
DELIMITER ;

-- --------------------------------------------------------

--
-- Table structure for table `posts`
--

CREATE TABLE `posts` (
  `post_pk` char(32) NOT NULL,
  `post_user_fk` char(32) NOT NULL,
  `post_message` varchar(280) NOT NULL,
  `post_image_path` varchar(255) NOT NULL,
  `post_total_likes` bigint(20) UNSIGNED NOT NULL DEFAULT 0,
  `post_total_comments` bigint(20) UNSIGNED NOT NULL DEFAULT 0,
  `post_created_at` bigint(20) UNSIGNED NOT NULL DEFAULT 0,
  `post_updated_at` bigint(20) UNSIGNED NOT NULL DEFAULT 0,
  `post_deleted_at` bigint(20) UNSIGNED NOT NULL DEFAULT 0,
  `post_is_blocked` tinyint(1) UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `posts`
--

INSERT INTO `posts` (`post_pk`, `post_user_fk`, `post_message`, `post_image_path`, `post_total_likes`, `post_total_comments`, `post_created_at`, `post_updated_at`, `post_deleted_at`, `post_is_blocked`) VALUES
('1e5ecc804e1f46bc8e723437bf4bfc4b', '225a9fc15b8f409aa5c8ee7eafee516b', 'And this just works!', 'post_3.jpeg', 0, 0, 1763825000, 0, 0, 0),
('258aeac7242348058c8c36f025b10fd5', '225a9fc15b8f409aa5c8ee7eafee516b', 'tes5', '', 0, 0, 1763825001, 0, 0, 0),
('28dd4c1671634d73acd29a0ab109bef1', '805a39cd8c854ee8a83555a308645bf5', 'My first super life !', 'post_3.jpeg', 0, 0, 1763825002, 0, 0, 0),
('299323cf81924589b0de265e715a1f9e', '225a9fc15b8f409aa5c8ee7eafee516b', 'test3', 'post_1.jpeg', 0, 0, 1763825003, 0, 0, 0),
('3cb78d73518c4c01a29ad33d196ce962', '225a9fc15b8f409aa5c8ee7eafee516b', 'This is new', '', 0, 0, 1763825004, 0, 0, 0),
('3e4f0c3ab65344d8b79c849400418758', '225a9fc15b8f409aa5c8ee7eafee516b', 'test1', '', 0, 0, 1763825005, 0, 0, 0),
('3f534678ba324c3aa2624c1f118573f7', '6b48c6095913402eb4841529830e5415', 'dfdfd', '', 0, 0, 1763825006, 0, 0, 0),
('4d7539e34cf64c48b887dfefe260b9b2', '6b48c6095913402eb4841529830e5415', 'sup?', '', 0, 0, 1763825093, 0, 0, 1),
('4ec81a4aaba249358dbb92e80514f58c', '6b48c6095913402eb4841529830e5415', 'bdljbdvlj vd', '', 0, 0, 1763825007, 0, 0, 0),
('50293af4d1f64798af9b7dfcbf5ed3e7', '225a9fc15b8f409aa5c8ee7eafee516b', 'new', '', 0, 0, 1763825008, 0, 0, 0),
('5b147eb4f0064bd9be7f18e6be2b3347', '225a9fc15b8f409aa5c8ee7eafee516b', 'First great test', '', 0, 0, 1763825009, 0, 0, 0),
('616c38c6e9e14406a92439e2d81490fc', '225a9fc15b8f409aa5c8ee7eafee516b', 'A browser', '', 0, 0, 1763825010, 0, 0, 0),
('63ed90b8cafc47fa9a3253fa1ecfeb04', '225a9fc15b8f409aa5c8ee7eafee516b', 'this', '', 0, 0, 1763825011, 0, 0, 0),
('69d3ed14f15047139b6cd8bd8180c104', '59ac8f8892bc45528a631d4415151f13', 'This is Daniel\'s post', '', 0, 0, 1763825012, 0, 0, 0),
('6a67456ad548482e9a5fd809ecc9b102', '6b48c6095913402eb4841529830e5415', 'xfljdjflngækndnkæ', '1d40fb2209ab4fa0b604ec288270b89b.png', 0, 1, 1764076091, 0, 0, 0),
('6b33c12e537b45669a247c5a38caccd2', '6b48c6095913402eb4841529830e5415', 'test', '', 0, 0, 1764076183, 0, 0, 1),
('6b7bc6fd2b57486db21325030f63fd90', '6b48c6095913402eb4841529830e5415', 'erere', '', 0, 0, 1763825013, 0, 0, 1),
('79c5470b54da40f5ac19729738b37a38', '6b48c6095913402eb4841529830e5415', 'dfdfd', '', 0, 0, 1763825014, 0, 0, 0),
('7d55a44b9d7e40a2b1982ce8f6b5cb8b', '6b48c6095913402eb4841529830e5415', 'test', '', 0, 0, 1764846284, 0, 0, 0),
('7d6f40e626c54efaa32494bce5f739d7', '88a93bb5267e443eb0047f421a7a2f34', 'test', 'post_2.jpeg', 0, 0, 1763825015, 0, 0, 1),
('99fefea24ea5419da19ed1f8cf8e9499', '225a9fc15b8f409aa5c8ee7eafee516b', 'wow', 'post_1.jpeg', 0, 0, 1763825016, 0, 0, 0),
('ad95e1d3f62f4d07b7bf9e3e6d4dd527', '225a9fc15b8f409aa5c8ee7eafee516b', 'And this just works!', '', 0, 0, 1763825017, 0, 0, 0),
('c49357e327324f72901ec8166a08c069', '6b48c6095913402eb4841529830e5415', 'works?', '', 0, 0, 1764254600, 0, 0, 0),
('d2a7dc6fbe61441498e547aa61f00bf8', '6b48c6095913402eb4841529830e5415', 'new', '6a391c35699640c6a170907fb4cc825f.jpeg', 0, 0, 1764253638, 0, 1764514394, 0);

-- --------------------------------------------------------

--
-- Table structure for table `trends`
--

CREATE TABLE `trends` (
  `trend_pk` char(32) NOT NULL,
  `trend_title` varchar(100) NOT NULL,
  `trend_message` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `trends`
--

INSERT INTO `trends` (`trend_pk`, `trend_title`, `trend_message`) VALUES
('6543c995d1af4ebcbd5280a4afaa1e2c', 'Politics are rotten', 'Everyone talks and only a few try to do something'),
('8343c995d1af4ebcbd5280a6afaa1e2d', 'New rocket to the moon', 'A new rocket has been sent towards the moon, but id didn\'t make it');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `user_pk` char(32) NOT NULL,
  `user_email` varchar(100) NOT NULL,
  `user_password` varchar(255) NOT NULL,
  `user_username` varchar(20) NOT NULL,
  `user_first_name` varchar(20) NOT NULL,
  `user_last_name` varchar(20) NOT NULL DEFAULT '',
  `user_avatar_path` varchar(50) NOT NULL,
  `user_total_followers` int(10) UNSIGNED NOT NULL DEFAULT 0,
  `user_password_reset` char(32) NOT NULL,
  `user_verification_key` char(32) NOT NULL,
  `user_verified_at` bigint(20) UNSIGNED NOT NULL,
  `user_updated_at` bigint(20) UNSIGNED NOT NULL,
  `user_deleted_at` bigint(20) UNSIGNED NOT NULL,
  `user_is_blocked` tinyint(1) UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`user_pk`, `user_email`, `user_password`, `user_username`, `user_first_name`, `user_last_name`, `user_avatar_path`, `user_total_followers`, `user_password_reset`, `user_verification_key`, `user_verified_at`, `user_updated_at`, `user_deleted_at`, `user_is_blocked`) VALUES
('21e66977ccb74fdbb6cbdb3e7e3a12cb', 'daniel@gmail.com', 'scrypt:32768:8:1$2hnap8BFIQCZIDhM$e17a59f7d106fe5ee8444c1e3474f6a2f9351f1cdd01d17b94897e3caa946b6a9566b03a89ccd1a3b679a8de0c2a13b27ca79c6a581aea384c985d43d72e7b80', 'daniel', 'Daniel', '', 'avatar_2.jpg', 0, '', '', 0, 0, 0, 0),
('225a9fc15b8f409aa5c8ee7eafee516b', 'a@aaa.com', 'scrypt:32768:8:1$wnse70hQwhCvR9tC$724c32a91b5f277201afbb141f9293a93168327df5c9124f482d3c32b8dff991c41629f477dfaee021965f9b15318a4257aad2e933101a4c998ef3c346fc84e4', 'santisss', 'Tester', '', 'avatar_1.jpg', 0, '', '', 455656, 0, 0, 0),
('38821e8c53b146b591933bed979e2016', 'testing@test.com', 'scrypt:32768:8:1$G4Qpwj0uN76FpdNQ$9d21ce2b9190a443fc13de3ab84ad3ff6ca33b44e14add8ad81b70684b84198b4212b9b0bb72669286d400ae50039c72242da19f1e0a003a324383f43bd8ea80', 'TesterUser', 'terse', '', 'default.jpg', 1, '', '50bbfc7c75014307a4123a1085c856c', 0, 0, 0, 0),
('393e59265baf4792894c06aa82155676', 'aaa@aaa.com', 'scrypt:32768:8:1$8ZCQ0uS75a0N08wf$63de014c83f6ccc991214910f7550e0b7922d85851a5b757210abe8d39edf6a05cb08d19bd0ccfdfa5870e5fad32ae7f8a34a02b073926c4910cfb2a67dc212b', 'TEstingAAAA', 'Test', '', 'avatar_2.jpg', 0, '', '', 1762338886, 0, 0, 0),
('3bb267bceca44e58883bbc29200d44e5', 'delete.testing@test.com', 'scrypt:32768:8:1$Tq056RbRH27Mc9g3$84810a2576e4828498be40c7f51f33e59d19d136e0c5c12e31fb676f3141934c639e088530f9be4ce682cbdfd4eaec34e1220fa7121bf8779e7de0bff29115b9', 'DeleteTesting', 'Delete', '', 'default.jpg', 0, '', '', 0, 0, 1763715642, 0),
('59ac8f8892bc45528a631d4415151f13', 'terese@gmail.com', 'scrypt:32768:8:1$Tq056RbRH27Mc9g3$84810a2576e4828498be40c7f51f33e59d19d136e0c5c12e31fb676f3141934c639e088530f9be4ce682cbdfd4eaec34e1220fa7121bf8779e7de0bff29115b9', 'Mily', 'Mille', '', 'default.jpg', 0, '', '', 45665656, 0, 0, 0),
('6b48c6095913402eb4841529830e5415', 'a@a.com', 'scrypt:32768:8:1$xKJ6OTjSVThuhCnh$ff295588848af6f759c3ee83f3ff96e9e921ee10d0e0023a2dab93422455bb610fc0f49ba2df99595b482da58015ddd3347b62fa0145d5a2e8e50c472ef39b0f', 'Tere', 'Terese', '', '4637d4990b4d4204b9153098a2726a79.avif', 0, '', '', 45445, 1763462249, 0, 0),
('805a39cd8c854ee8a83555a308645bf5', 'fullflaskdemomail@gmail.com', 'scrypt:32768:8:1$VlBgiW1xFsZuKRML$a5f61d62ac3f45d42c58cf8362637e717793b8760f026b1b47b7bfec47037abbe13e1c20e8bdc66fc03cc153d0bcf6185e15cf25ad58eb9d344267882dd7e78c', 'santiago', 'Santiago', '', 'avatar_3.jpg', 0, '', '', 565656, 0, 0, 1),
('88a93bb5267e443eb0047f421a7a2f34', 'santi@gmail.com', 'scrypt:32768:8:1$PEIO0eliDPqnCCbw$acb791128831bc90030ac363e4b76db196689bd99c1ccde5c2c20a7d4fe909e07129f3f4fd4f086e347375edbb8229e9ba5dc126cc14f6107fb1fc2abf6498f8', 'gustav', 'Gustav', '', 'avatar_2.jpg', 0, '', '', 54654564, 0, 0, 0),
('88b7531588de415f82255ffd24a47137', 'new.test@test.com', 'scrypt:32768:8:1$hOMOK59rhMvbEU5P$6bc18b16b5b3952040cd4fdf017a17eb5e5e1a391932b3edc4e613434176e936f63c33b617a9ddc7d7282a5a6dbf27ba36ab462903af3126650fd50608697948', 'testingSinging', 'test', '', 'default.jpg', 0, '', '9e1a0dd9230341f89f25b8dbf59bab9d', 0, 0, 0, 0),
('92a3bd84a00a46f8b6862caaf192875a', 'b@b.com', 'scrypt:32768:8:1$8GK1ZiI0cxhJSv6q$d82dccd945d0f905c51c3564dc7197fb18beea2260f5c10a3c8f93a785f74b45c166471605c1a5ccd9423154e53a0b67d53248f77a5331644a54e8a8a439a994', 'btester', 'test', '', 'default.jpg', 0, '', '', 1763717309, 0, 0, 1);

--
-- Indexes for dumped tables
--

--
-- Indexes for table `comments`
--
ALTER TABLE `comments`
  ADD PRIMARY KEY (`comment_pk`);

--
-- Indexes for table `follows`
--
ALTER TABLE `follows`
  ADD PRIMARY KEY (`followed_fk`,`follower_fk`);

--
-- Indexes for table `likes`
--
ALTER TABLE `likes`
  ADD PRIMARY KEY (`liked_post_fk`,`liker_user_fk`);

--
-- Indexes for table `posts`
--
ALTER TABLE `posts`
  ADD PRIMARY KEY (`post_pk`),
  ADD UNIQUE KEY `post_pk` (`post_pk`),
  ADD KEY `post_created_at` (`post_created_at`);

--
-- Indexes for table `trends`
--
ALTER TABLE `trends`
  ADD UNIQUE KEY `trend_pk` (`trend_pk`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`user_pk`),
  ADD UNIQUE KEY `user_pk` (`user_pk`),
  ADD UNIQUE KEY `user_email` (`user_email`),
  ADD UNIQUE KEY `user_name` (`user_username`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
