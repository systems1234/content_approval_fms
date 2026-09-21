import NextAuth from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import { getUserByEmail } from '@/lib/store'

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId:     process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          hd: process.env.GOOGLE_WORKSPACE_DOMAIN || 'gempundit.com',
          prompt: 'select_account',
        },
      },
    }),
  ],
  callbacks: {
    async signIn({ user }) {
      const email = (user.email ?? '').toLowerCase()
      const domain = process.env.GOOGLE_WORKSPACE_DOMAIN || 'gempundit.com'

      // Must be @gempundit.com
      if (!email.endsWith(`@${domain}`)) return false

      // Must have a row in Users table
      const dbUser = await getUserByEmail(email)
      if (!dbUser || !dbUser.isActive) return false

      return true
    },
    async session({ session }) {
      if (session.user?.email) {
        const dbUser = await getUserByEmail(session.user.email)
        if (dbUser) {
          ;((session as unknown) as Record<string, unknown>).dbUser = {
            id: dbUser.id,
            username: dbUser.username,
            email: dbUser.email,
            role: dbUser.role,
            isActive: dbUser.isActive,
          }
        }
      }
      return session
    },
  },
  pages: {
    signIn: '/signin',
    error: '/signin',
  },
  secret: process.env.NEXTAUTH_SECRET,
})

export { handler as GET, handler as POST }
