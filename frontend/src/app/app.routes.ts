import { Routes } from '@angular/router';

import { HomePage } from './pages/homePage/home';
import { LoginPage } from './pages/loginPage/login';
import { RegisterPage } from './pages/register/register';
import { NotFoundPage } from './pages/notFoundPage/notFound';
import { ChannelsPage } from './pages/channelsPage/channels';
import { TelegramComponent } from './pages/telegramPage/telegram';
import { authGuard } from './core/guards/authGuard';
import { ProfilePage } from './pages/profilePage/profile';



export const routes: Routes = [
    {path: '', component: HomePage, title: 'IRKA', canActivate: [authGuard]},
    {path: 'login', component: LoginPage, title: 'Login'},
    {path: 'register', component: RegisterPage, title: 'Register'},
    {path: 'telegram', component: TelegramComponent, title: 'Telegram Verification', canActivate: [authGuard]},
    {path: 'channels', component: ChannelsPage, title: 'Channels', canActivate: [authGuard]},
    {path: 'profile', component: ProfilePage, title: 'Profile', canActivate: [authGuard]},
    {path: '**', component: NotFoundPage, title: 'Not Found', canActivate: [authGuard]},
];
