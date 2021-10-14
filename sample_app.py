from googleapiclient.discovery import build

import json
import pandas as pd
import streamlit as st


DEVELOPER_KEY = st.secrets["KEY"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION,
                developerKey=DEVELOPER_KEY)


def serch_video(youtube, q='自動化', max_results=50):

    response = youtube.search().list(
        q=q,
        part="id,snippet",
        order='viewCount',
        type='video',
        maxResults=max_results
    ).execute()

    items_id = []
    items = response['items']
    for item in items:
        item_id = {}
        item_id['video_id'] = item['id']['videoId']
        item_id['channel_id'] = item['snippet']['channelId']
        items_id.append(item_id)

    df_video = pd.DataFrame(items_id)

    return df_video


def get_results(df_video, threshold=5000):
    channel_ids = df_video['channel_id'].unique().tolist()
    subscriber_list = youtube.channels().list(
        id=','.join(channel_ids),
        part='statistics',
        fields='items(id, statistics(subscriberCount))'
    ).execute()

    subscribers = []
    for item in subscriber_list['items']:
        subscriber = {}
        if len(item['statistics']) > 0:
            subscriber['channel_id'] = item['id']
            subscriber['subscriber_count'] = int(
                item['statistics']['subscriberCount'])
        else:
            subscriber['channel_id'] = item['id']
        subscribers.append(subscriber)

    df_subscribers = pd.DataFrame(subscribers)

    df = pd.merge(left=df_video, right=df_subscribers, on='channel_id')
    df_extracted = df[df['subscriber_count'] < threshold]

    video_ids = df_extracted['video_id'].to_list()
    videos_list = youtube.videos().list(
        id=','.join(video_ids),
        part='snippet, statistics',
        fields='items(id, snippet(title,publishedAt),contentDetails(duration),statistics(viewCount))'
    ).execute()

    videos_info = []
    items = videos_list['items']
    for item in items:
        video_info = {}
        video_info['video_id'] = item['id']
        video_info['title'] = item['snippet']['title']
        video_info['view_count'] = item['statistics']['viewCount']
        videos_info.append(video_info)

    df_videos_info = pd.DataFrame(videos_info)

    try:
        results = pd.merge(left=df_extracted,
                           right=df_videos_info, on='video_id')
        results = results.loc[:, ['video_id', 'title',
                                  'view_count', 'subscriber_count', 'channel_id']]
    except:
        results = pd.DataFrame()

    return results


st.title('Youtube分析アプリサンプル')

st.sidebar.write('## 検索ワードと登録者数の設定')
st.sidebar.write('### 検索ワードの入力')
query = st.sidebar.text_input('検索ワードを入力してください')

st.sidebar.write('## 登録者数の設定')
threshold = st.sidebar.slider('登録者数の閾値', 100, 5000000, 5000)

st.sidebar.write('## 結果表示件数の設定')
max_result = st.sidebar.slider('表示件数の設定', 5, 100, 10)

st.write('### 選択中のパラメーター')
st.write('(サイドバーで調節してください)')
st.markdown(f"""
- 検索ワード：{query}         
- 登録者数：{threshold}
- 表示件数：{max_result}
""")

df_video = serch_video(youtube, q=query, max_results=max_result)
results = get_results(df_video, threshold=threshold)

st.write('### 検索結果', results)
st.write('### 動画再生')

video_id = st.text_input('動画ID（video_id）をコピーして貼り付けてください')
url = f'https://youtu.be/{video_id}'

video_field = st.empty()
video_field.write('こちらに動画が表示されます')

if st.button('ビデオ表示'):
    if len(video_id) > 0:
        try:
            video_field.video(url)
        except:
            st.error('おっと何かエラーが起きているようです')
