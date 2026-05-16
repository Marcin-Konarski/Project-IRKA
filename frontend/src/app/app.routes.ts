import { Routes } from '@angular/router';

import { HomePage } from './pages/homePage/home';
import { LoginPage } from './pages/loginPage/login';
import { RegisterPage } from './pages/register/register';
import { NotFoundPage } from './pages/notFoundPage/notFound';
import { ChannelsPage } from './pages/channelsPage/channels';
import { TelegramComponent } from './pages/telegramPage/telegram';



export const routes: Routes = [
    {path: '', component: HomePage, title: 'DarkCTI'},
    {path: 'home', component: HomePage, title: 'Home'},
    {path: 'login', component: LoginPage, title: 'Login'},
    {path: 'register', component: RegisterPage, title: 'Register'},
    {path: 'telegram', component: TelegramComponent, title: 'Telegram Verification'},
    {path: 'channels', component: ChannelsPage, title: 'Channels'},
    {path: '**', component: NotFoundPage, title: 'Not Found'},
];
