import type { NextPage } from 'next';
import Head from 'next/head';
import styles from '../styles/Home.module.css';
import { PostFeed } from '../components/PostFeed';
import { Navigation } from '../components/Navigation';

const Home: NextPage = () => {
  return (
    <div className={styles.container}>
      <Head>
        <title>Hive</title>
        <meta
          content="Decentralized social media on Base"
          name="description"
        />
        <link href="/favicon.ico" rel="icon" />
      </Head>

      <Navigation />

      <main className={styles.main}>
        <h1 className={styles.title}>
          Welcome to Hive
        </h1>

        <p className={styles.description}>
          Your decentralized social feed
        </p>

        <PostFeed />
      </main>

      <footer className={styles.footer}>
        Built for EthOnline 2025
      </footer>
    </div>
  );
};

export default Home;
