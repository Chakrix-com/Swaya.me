import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout, Row, Col, Typography, Button, Input, Card, Space, Divider } from 'antd';
import {
  LoginOutlined,
  UserAddOutlined,
  PlayCircleOutlined,
  QuestionCircleOutlined,
  TrophyOutlined,
  TeamOutlined,
  DashboardOutlined,
  RocketOutlined
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '../../components/LanguageSwitcher';
import './Home.css';

const { Header, Content, Footer } = Layout;
const { Title, Paragraph, Text } = Typography;

const Home = () => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [joinCode, setJoinCode] = useState('');

  const handleJoinQuiz = () => {
    if (joinCode.trim()) {
      navigate(`/join/${joinCode.trim().toUpperCase()}`);
    }
  };

  const features = [
    {
      icon: <QuestionCircleOutlined style={{ fontSize: '48px', color: '#1890ff' }} />,
      title: t('home.features.createQuizzes'),
      description: t('home.features.createQuizzesDesc')
    },
    {
      icon: <TeamOutlined style={{ fontSize: '48px', color: '#52c41a' }} />,
      title: t('home.features.liveParticipation'),
      description: t('home.features.liveParticipationDesc')
    },
    {
      icon: <DashboardOutlined style={{ fontSize: '48px', color: '#722ed1' }} />,
      title: t('home.features.realTimeResults'),
      description: t('home.features.realTimeResultsDesc')
    },
    {
      icon: <TrophyOutlined style={{ fontSize: '48px', color: '#faad14' }} />,
      title: t('home.features.wordClouds'),
      description: t('home.features.wordCloudsDesc')
    }
  ];

  return (
    <Layout className="home-layout">
      <Header className="home-header">
        <div className="home-header-content">
          <div className="home-logo">
            <RocketOutlined style={{ fontSize: '32px', marginRight: '12px' }} />
            <Title level={2} style={{ margin: 0, color: 'white' }}>Swaya.me</Title>
          </div>
          <Space size="middle">
            <LanguageSwitcher />
            <Button 
              type="text" 
              icon={<LoginOutlined />}
              onClick={() => navigate('/login')}
              style={{ color: 'white' }}
            >
              {t('home.login')}
            </Button>
            <Button 
              type="primary"
              icon={<UserAddOutlined />}
              onClick={() => navigate('/register')}
            >
              {t('home.signup')}
            </Button>
          </Space>
        </div>
      </Header>

      <Content className="home-content">
        {/* Hero Section */}
        <div className="hero-section">
          <Row justify="center" align="middle">
            <Col xs={24} sm={20} md={18} lg={16} xl={14}>
              <div className="hero-content">
                <Title level={1} className="hero-title">
                  {t('home.hero.title')}
                </Title>
                <Paragraph className="hero-subtitle">
                  {t('home.hero.subtitle')}
                </Paragraph>

                {/* Quick Join Section */}
                <Card className="quick-join-card" bordered={false}>
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <div>
                      <Text strong style={{ fontSize: '16px', display: 'block', marginBottom: '12px' }}>
                        <PlayCircleOutlined /> {t('home.quickJoin.title')}
                      </Text>
                      <Input.Search
                        size="large"
                        placeholder={t('home.quickJoin.placeholder')}
                        enterButton={t('home.quickJoin.button')}
                        value={joinCode}
                        onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
                        onSearch={handleJoinQuiz}
                        style={{ maxWidth: '500px' }}
                      />
                    </div>

                    <Divider style={{ margin: '12px 0' }}>{t('home.quickJoin.or')}</Divider>

                    <Space size="middle" wrap>
                      <Button 
                        type="primary" 
                        size="large"
                        icon={<UserAddOutlined />}
                        onClick={() => navigate('/register')}
                      >
                        {t('home.quickJoin.createAccount')}
                      </Button>
                      <Button 
                        size="large"
                        onClick={() => navigate('/login')}
                      >
                        {t('home.quickJoin.existingUser')}
                      </Button>
                    </Space>
                  </Space>
                </Card>
              </div>
            </Col>
          </Row>
        </div>

        {/* Features Section */}
        <div className="features-section">
          <Row justify="center">
            <Col xs={24} sm={20} md={18} lg={16} xl={14}>
              <Title level={2} style={{ textAlign: 'center', marginBottom: '48px' }}>
                {t('home.features.title')}
              </Title>
              <Row gutter={[24, 24]}>
                {features.map((feature, index) => (
                  <Col xs={24} sm={12} md={12} lg={6} key={index}>
                    <Card className="feature-card" bordered={false}>
                      <div style={{ textAlign: 'center' }}>
                        {feature.icon}
                        <Title level={4} style={{ marginTop: '16px' }}>
                          {feature.title}
                        </Title>
                        <Paragraph type="secondary">
                          {feature.description}
                        </Paragraph>
                      </div>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Col>
          </Row>
        </div>

        {/* CTA Section */}
        <div className="cta-section">
          <Row justify="center">
            <Col xs={24} sm={20} md={16} lg={12}>
              <Card className="cta-card" bordered={false}>
                <Title level={2} style={{ textAlign: 'center', color: 'white' }}>
                  {t('home.cta.title')}
                </Title>
                <Paragraph style={{ textAlign: 'center', color: 'rgba(255,255,255,0.85)', fontSize: '16px' }}>
                  {t('home.cta.subtitle')}
                </Paragraph>
                <div style={{ textAlign: 'center', marginTop: '32px' }}>
                  <Button 
                    type="primary" 
                    size="large"
                    icon={<UserAddOutlined />}
                    onClick={() => navigate('/register')}
                    style={{ 
                      height: '48px', 
                      fontSize: '16px',
                      background: 'white',
                      color: '#1890ff',
                      border: 'none'
                    }}
                  >
                    {t('home.cta.button')}
                  </Button>
                </div>
              </Card>
            </Col>
          </Row>
        </div>
      </Content>

      <Footer className="home-footer">
        <Text type="secondary">
          © 2026 Swaya.me. {t('home.footer.rights')}
        </Text>
      </Footer>
    </Layout>
  );
};

export default Home;
