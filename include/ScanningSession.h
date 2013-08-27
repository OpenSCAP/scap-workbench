/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#ifndef SCAP_WORKBENCH_SCANNING_SESSION_H_
#define SCAP_WORKBENCH_SCANNING_SESSION_H_

#include "ForwardDecls.h"
#include <QObject>
#include <QTemporaryFile>

extern "C"
{
#include <xccdf_benchmark.h>
}

/**
 */
class ScanningSession : public QObject
{
    Q_OBJECT

    public:
        ScanningSession(QObject* parent = 0);
        ~ScanningSession();

    public slots:
        /**
         * @brief Opens a specific file
         *
         * Passed file may be an XCCDF file (any openscap supported version)
         * or source datastream (SDS) file (any openscap supported version)
         */
        void openFile(const QString& path);

        /**
         * @brief Closes currently opened file (if any)
         */
        void closeFile();

        bool isSDS() const;

        void setDatastreamID(const QString& datastreamID);
        void setComponentID(const QString& componentID);

        void ensureTailoringExists();
        void resetTailoring();
        void setTailoringFile(const QString& tailoringFile);
        void setTailoringComponentID(const QString& componentID);

        bool setProfileID(const QString& profileID);

        /**
         * @brief Reloads the session if needed, datastream split is potentially done again
         *
         * @param forceReload if true, the reload is forced no matter what mSessionDirty is
         *
         * The main purpose of this method is to allow to reload the session when
         * parameters that affect "loading" of the session change. These parameters
         * are mainly datastream ID and component ID.
         *
         * mSessionDirty is automatically set to true whenever crucial parameters of
         * the session change. reloadSession will early out if reload is not necessary.
         */
        void reloadSession(bool forceReload = false) const;

        QString getInputFile() const;

        struct xccdf_session* getXCCDFSession() const;

        /**
         * @brief Returns true if a file has been opened in this session
         *
         * @note Never throws exceptions!
         */
        bool fileOpened() const;

        bool profileSelected() const;
        bool isSelectedProfileTailoring() const;

        /**
         * @brief Creates a new profile, makes it inherit current profile
         *
         * @param shadowed if true the new profile will have the same ID
         * @return created profile (can be passed to TailoringWindow for further tailoring)
         */
        struct xccdf_profile* tailorCurrentProfile(bool shadowed = false);

        QString getTailoringFile();

        bool hasTailoring() const;

    private:
        struct xccdf_benchmark* getXCCDFInputBenchmark();

        /// This is our central point of interaction with openscap
        struct xccdf_session* mSession;
        /// Our own tailoring that may or may not initially be loaded from a file
        mutable struct xccdf_tailoring* mTailoring;

        QTemporaryFile mTailoringFile;

        /// If true, the session will be reloaded
        mutable bool mSessionDirty;
        /// If true, we no longer allow changing tailoring entirely
        /// (loading new file, setting it to load from datastream, ...)
        /// user changes to the tailoring would be lost if we reloaded.
        bool mTailoringUserChanges;
};

#endif
